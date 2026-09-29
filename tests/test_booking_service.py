from app.core.enums import MessageRole
from app.schemas.booking import BookingExtraction, BookingSlots
from app.schemas.chat import ChatMessage
from app.services.booking_service import BookingService


class RecordingLLM:
    def __init__(self, replies: list[str]) -> None:
        self._replies = list(replies)

    async def complete(
        self, messages: object, *, json_mode: bool = False, temperature: float = 0.2
    ) -> str:
        return self._replies.pop(0)


def test_merge_keeps_previous_fields_and_fills_new_ones() -> None:
    existing = BookingSlots(name="Prasna", email=None, interview_date=None, interview_time=None)
    extraction = BookingExtraction(wants_to_book=True, email="p@example.com")

    merged = BookingService.merge(existing, extraction)

    assert merged.name == "Prasna"
    assert merged.email == "p@example.com"
    assert merged.missing_fields() == ["interview_date", "interview_time"]


def test_next_prompt_asks_for_first_missing_field() -> None:
    slots = BookingSlots(name="Prasna")
    assert "email" in BookingService.next_prompt(slots).lower()


async def test_extract_returns_not_booking_on_malformed_json() -> None:
    llm = RecordingLLM(["not valid json"])
    service = BookingService(llm, repository=None)  # type: ignore[arg-type]

    result = await service.extract([], "hi", BookingSlots())

    assert result.wants_to_book is False


async def test_extract_parses_valid_json() -> None:
    llm = RecordingLLM(
        [
            '{"wants_to_book": true, "name": "Prasna", "email": null, '
            '"interview_date": "2026-10-05", "interview_time": "14:00"}'
        ]
    )
    service = BookingService(llm, repository=None)  # type: ignore[arg-type]

    result = await service.extract(
        [ChatMessage(role=MessageRole.USER, content="book me for Oct 5 at 2pm")],
        "my name is Prasna",
        BookingSlots(),
    )

    assert result.wants_to_book is True
    assert result.name == "Prasna"
    assert result.interview_date is not None