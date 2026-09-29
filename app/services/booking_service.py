import json
import logging
from datetime import date

from pydantic import ValidationError

from app.db.models import Booking
from app.llm.base import ChatLLM, LLMMessage
from app.repositories.booking_repository import BookingRepository
from app.schemas.booking import BookingExtraction, BookingSlots
from app.schemas.chat import ChatMessage
from app.services.prompts import BOOKING_EXTRACTION_PROMPT

logger = logging.getLogger(__name__)

_FIELD_PROMPTS: dict[str, str] = {
    "name": "What name should I book the interview under?",
    "email": "What email address should I send the confirmation to?",
    "interview_date": "What date would you like the interview (e.g. 2026-10-05)?",
    "interview_time": "What time works for you (e.g. 14:00)?",
}


class BookingService:
    """Slot-filling interview booking, driven by one JSON-mode LLM call per turn."""

    def __init__(self, llm: ChatLLM, repository: BookingRepository) -> None:
        self._llm = llm
        self._repository = repository

    async def extract(
        self, history: list[ChatMessage], message: str, existing: BookingSlots
    ) -> BookingExtraction:
        transcript = "\n".join(
            f"{'User' if m.role.value == 'user' else 'Assistant'}: {m.content}" for m in history
        )
        prompt = BOOKING_EXTRACTION_PROMPT.format(
            today=date.today().isoformat(), transcript=transcript or "(none yet)", message=message
        )
        messages: list[LLMMessage] = [{"role": "user", "content": prompt}]

        raw = await self._llm.complete(messages, json_mode=True, temperature=0.0)
        try:
            extraction = BookingExtraction.model_validate_json(raw)
        except (ValidationError, json.JSONDecodeError):
            logger.warning("Could not parse booking extraction: %s", raw)
            return BookingExtraction(wants_to_book=False)

        return extraction

    @staticmethod
    def merge(existing: BookingSlots, extraction: BookingExtraction) -> BookingSlots:
        """New non-null fields win; previously collected fields are kept."""
        return BookingSlots(
            name=extraction.name or existing.name,
            email=extraction.email or existing.email,
            interview_date=extraction.interview_date or existing.interview_date,
            interview_time=extraction.interview_time or existing.interview_time,
        )

    @staticmethod
    def next_prompt(slots: BookingSlots) -> str:
        missing = slots.missing_fields()
        return _FIELD_PROMPTS[missing[0]]

    async def save(self, session_id: str, slots: BookingSlots) -> Booking:
        assert slots.name and slots.email and slots.interview_date and slots.interview_time
        booking = Booking(
            session_id=session_id,
            name=slots.name,
            email=slots.email,
            interview_date=slots.interview_date,
            interview_time=slots.interview_time,
        )
        return await self._repository.add(booking)