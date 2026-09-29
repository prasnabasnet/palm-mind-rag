from app.schemas.booking import BookingSlots
from app.schemas.chat import ChatMessage, SourceReference
from app.services.booking_service import BookingService
from app.services.memory_service import ChatMemory
from app.services.rag_service import RagService


class ChatTurnResult:
    def __init__(
        self, reply: str, sources: list[SourceReference], booking_confirmed: bool
    ) -> None:
        self.reply = reply
        self.sources = sources
        self.booking_confirmed = booking_confirmed


class ChatService:
    def __init__(
        self,
        rag_service: RagService,
        booking_service: BookingService,
        memory: ChatMemory,
    ) -> None:
        self._rag_service = rag_service
        self._booking_service = booking_service
        self._memory = memory

    async def handle_message(self, session_id: str, message: str) -> ChatTurnResult:
        pending_raw = await self._memory.get_pending_booking(session_id)
        existing = BookingSlots.model_validate_json(pending_raw) if pending_raw else BookingSlots()
        history = await self._memory.get_history(session_id)

        extraction = await self._booking_service.extract(history, message, existing)

        if not extraction.wants_to_book and existing.missing_fields() == [
            "name", "email", "interview_date", "interview_time"
        ]:
            # No booking in progress and this turn isn't starting one: normal RAG turn.
            result = await self._rag_service.answer(session_id, message)
            return ChatTurnResult(result.answer, result.sources, booking_confirmed=False)

        slots = self._booking_service.merge(existing, extraction)
        await self._memory.append(
            session_id, [ChatMessage(role="user", content=message)]  
        )

        if not slots.is_complete():
            await self._memory.set_pending_booking(session_id, slots.model_dump_json())
            reply = self._booking_service.next_prompt(slots)
            await self._memory.append(
                session_id, [ChatMessage(role="assistant", content=reply)]  
            )
            return ChatTurnResult(reply, [], booking_confirmed=False)

        await self._booking_service.save(session_id, slots)
        await self._memory.clear_pending_booking(session_id)
        reply = (
            f"You're booked, {slots.name}! Interview confirmed for "
            f"{slots.interview_date} at {slots.interview_time}. "
            f"A confirmation will be sent to {slots.email}."
        )
        await self._memory.append(
            session_id, [ChatMessage(role="assistant", content=reply)]  
        )
        return ChatTurnResult(reply, [], booking_confirmed=True)