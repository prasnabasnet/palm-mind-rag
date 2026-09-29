import uuid

from pydantic import BaseModel

from app.core.enums import MessageRole


class ChatMessage(BaseModel):
    role: MessageRole
    content: str


class SourceReference(BaseModel):
    document_id: uuid.UUID
    filename: str
    chunk_index: int
    score: float