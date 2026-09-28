import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.enums import ChunkingStrategy, DocumentStatus


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    content_type: str
    file_size_bytes: int
    chunking_strategy: ChunkingStrategy
    chunk_count: int
    status: DocumentStatus
    error_message: str | None
    created_at: datetime