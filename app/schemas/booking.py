import uuid
from datetime import date, datetime, time

from pydantic import BaseModel, EmailStr


class BookingSlots(BaseModel):
    """Partial or complete booking data collected across turns."""

    name: str | None = None
    email: str | None = None
    interview_date: date | None = None
    interview_time: time | None = None

    def missing_fields(self) -> list[str]:
        fields = {
            "name": self.name,
            "email": self.email,
            "interview_date": self.interview_date,
            "interview_time": self.interview_time,
        }
        return [name for name, value in fields.items() if value is None]

    def is_complete(self) -> bool:
        return not self.missing_fields()


class BookingExtraction(BaseModel):
    """What the LLM returns after reading the conversation."""

    wants_to_book: bool
    name: str | None = None
    email: str | None = None
    interview_date: date | None = None
    interview_time: time | None = None


class BookingResponse(BaseModel):
    id: uuid.UUID
    session_id: str
    name: str
    email: EmailStr
    interview_date: date
    interview_time: time
    created_at: datetime

    model_config = {"from_attributes": True}