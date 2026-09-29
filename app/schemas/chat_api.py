import uuid

from pydantic import BaseModel, Field

from app.schemas.chat import SourceReference


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    sources: list[SourceReference]
    booking_confirmed: bool


class BookingSummary(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    interview_date: str
    interview_time: str