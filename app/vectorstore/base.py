import uuid
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ChunkRecord:
    document_id: uuid.UUID
    chunk_index: int
    text: str
    filename: str


@dataclass(frozen=True, slots=True)
class SearchHit:
    document_id: uuid.UUID
    chunk_index: int
    text: str
    filename: str
    score: float


class VectorStore(Protocol):
    async def ensure_collection(self, dimension: int) -> None: ...

    async def upsert_chunks(
        self, records: list[ChunkRecord], vectors: list[list[float]]
    ) -> None: ...

    async def search(self, vector: list[float], limit: int) -> list[SearchHit]: ...

    async def delete_document(self, document_id: uuid.UUID) -> None: ...