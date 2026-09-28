import uuid

import pytest

from app.core.enums import ChunkingStrategy, DocumentStatus
from app.core.exceptions import FileTooLargeError, IngestionError
from app.db.models import Document
from app.repositories.document_repository import DocumentRepository
from app.services.ingestion_service import IngestionService
from app.vectorstore.base import ChunkRecord


class FakeRepository:
    def __init__(self) -> None:
        self.documents: dict[uuid.UUID, Document] = {}

    async def add(self, document: Document) -> Document:
        document.id = uuid.uuid4()
        self.documents[document.id] = document
        return document

    async def save(self, document: Document) -> Document:
        return document


class FakeEmbedder:
    dimension = 3

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in texts]

    async def embed_query(self, text: str) -> list[float]:
        return [0.1, 0.2, 0.3]


class FailingEmbedder(FakeEmbedder):
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise RuntimeError("model exploded")


class FakeVectorStore:
    def __init__(self) -> None:
        self.records: list[ChunkRecord] = []
        self.deleted: list[uuid.UUID] = []

    async def ensure_collection(self, dimension: int) -> None:
        return None

    async def upsert_chunks(
        self, records: list[ChunkRecord], vectors: list[list[float]]
    ) -> None:
        self.records.extend(records)

    async def search(self, vector: list[float], limit: int) -> list[object]:
        return []

    async def delete_document(self, document_id: uuid.UUID) -> None:
        self.deleted.append(document_id)


def make_service(
    embedder: FakeEmbedder, store: FakeVectorStore, max_bytes: int = 1_000_000
) -> IngestionService:
    repository: DocumentRepository = FakeRepository()  # type: ignore[assignment]
    return IngestionService(repository, embedder, store, max_bytes)  # type: ignore[arg-type]


async def test_ingest_completes_and_stores_chunks() -> None:
    store = FakeVectorStore()
    service = make_service(FakeEmbedder(), store)

    document = await service.ingest(
        "notes.txt", "text/plain", b"One. Two. Three.", ChunkingStrategy.SENTENCE
    )

    assert document.status == DocumentStatus.COMPLETED
    assert document.chunk_count == len(store.records) > 0


async def test_ingest_failure_marks_failed_and_cleans_up() -> None:
    store = FakeVectorStore()
    service = make_service(FailingEmbedder(), store)

    with pytest.raises(IngestionError):
        await service.ingest("notes.txt", "text/plain", b"Hello there.", ChunkingStrategy.FIXED)

    assert len(store.deleted) == 1


async def test_ingest_rejects_oversized_file() -> None:
    service = make_service(FakeEmbedder(), FakeVectorStore(), max_bytes=10)

    with pytest.raises(FileTooLargeError):
        await service.ingest("big.txt", "text/plain", b"x" * 11, ChunkingStrategy.FIXED)