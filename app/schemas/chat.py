from pydantic import BaseModel

from app.core.enums import MessageRole


class ChatMessage(BaseModel):
    role: MessageRole
    content: str