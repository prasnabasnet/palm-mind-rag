import asyncio
import contextlib
import logging
import uuid
from pathlib import Path

from app.chunking.factory import get_chunker
from app.core.enums import ChunkingStrategy, DocumentStatus
from app.core.exceptions import (
    DocumentNotFoundError,
    EmptyDocumentError,
    FileTooLargeError,
    IngestionError,
)
from app.db.models import Document
from app.embeddings.base import Embedder
from app.extraction.factory import extract_text
from app.repositories.document_repository import DocumentRepository
from app.vectorstore.base import ChunkRecord, VectorStore

logger = logging.getLogger(__name__)


class IngestionService:
    def __init__(
        self,
        repository: DocumentRepository,
        embedder: Embedder,
        vector_store: VectorStore,
        max_upload_bytes: int,
    ) -> None:
        self._repository = repository
        self._embedder = embedder
        self._vector_store = vector_store
        self._max_upload_bytes = max_upload_bytes

    async def ingest(
        self,
        filename: str,
        content_type: str,
        data: bytes,
        strategy: ChunkingStrategy,
    ) -> Document:
        if len(data) > self._max_upload_bytes:
            raise FileTooLargeError(
                f"File exceeds the {self._max_upload_bytes // (1024 * 1024)} MB limit."
            )

        safe_name = Path(filename).name
        # PDF parsing is CPU-bound and synchronous, so keep it off the event loop.
        text = await asyncio.to_thread(extract_text, safe_name, data)
        chunks = get_chunker(strategy).chunk(text)
        if not chunks:
            raise EmptyDocumentError("No text chunks could be produced from the document.")

        document = await self._repository.add(
            Document(
                filename=safe_name,
                content_type=content_type,
                file_size_bytes=len(data),
                chunking_strategy=strategy,
                chunk_count=0,
                status=DocumentStatus.PROCESSING,
            )
        )

        try:
            vectors = await self._embedder.embed_documents([c.text for c in chunks])
            records = [ChunkRecord(document.id, c.index, c.text, safe_name) for c in chunks]
            await self._vector_store.upsert_chunks(records, vectors)
        except Exception as exc:
            logger.exception("Ingestion failed for document %s", document.id)
            with contextlib.suppress(Exception):
                await self._vector_store.delete_document(document.id)
            document.status = DocumentStatus.FAILED
            document.error_message = str(exc)[:500]
            await self._repository.save(document)
            raise IngestionError("Failed to embed or store the document.") from exc

        document.status = DocumentStatus.COMPLETED
        document.chunk_count = len(chunks)
        return await self._repository.save(document)

    async def get_document(self, document_id: uuid.UUID) -> Document:
        document = await self._repository.get(document_id)
        if document is None:
            raise DocumentNotFoundError(f"Document {document_id} not found.")
        return document

    async def list_documents(self, limit: int, offset: int) -> list[Document]:
        return await self._repository.list_documents(limit, offset)

    async def delete_document(self, document_id: uuid.UUID) -> None:
        document = await self.get_document(document_id)
        await self._vector_store.delete_document(document.id)
        await self._repository.delete(document)