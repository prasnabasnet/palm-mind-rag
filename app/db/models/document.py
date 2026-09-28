import uuid

from sqlalchemy import Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import ChunkingStrategy, DocumentStatus
from app.db.base import Base, TimestampMixin


class Document(TimestampMixin, Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    file_size_bytes: Mapped[int] = mapped_column(Integer)
    chunking_strategy: Mapped[ChunkingStrategy] = mapped_column(
        Enum(ChunkingStrategy, native_enum=False, length=20)
    )
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, native_enum=False, length=20),
        default=DocumentStatus.PROCESSING,
    )
    error_message: Mapped[str | None] = mapped_column(String(500), default=None)