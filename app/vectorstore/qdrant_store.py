import uuid

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    FilterSelector,
    MatchValue,
    PointStruct,
    ScoredPoint,
    VectorParams,
)

from app.vectorstore.base import ChunkRecord, SearchHit

_BATCH_SIZE = 64


def _point_id(document_id: uuid.UUID, chunk_index: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{document_id}:{chunk_index}"))


def _to_hit(point: ScoredPoint) -> SearchHit:
    payload = point.payload or {}
    return SearchHit(
        document_id=uuid.UUID(str(payload["document_id"])),
        chunk_index=int(payload["chunk_index"]),
        text=str(payload["text"]),
        filename=str(payload["filename"]),
        score=point.score,
    )


class QdrantVectorStore:
    def __init__(self, client: AsyncQdrantClient, collection: str) -> None:
        self._client = client
        self._collection = collection

    async def ensure_collection(self, dimension: int) -> None:
        if await self._client.collection_exists(self._collection):
            return
        await self._client.create_collection(
            collection_name=self._collection,
            vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
        )

    async def upsert_chunks(
        self, records: list[ChunkRecord], vectors: list[list[float]]
    ) -> None:
        points = [
            PointStruct(
                id=_point_id(record.document_id, record.chunk_index),
                vector=vector,
                payload={
                    "document_id": str(record.document_id),
                    "chunk_index": record.chunk_index,
                    "text": record.text,
                    "filename": record.filename,
                },
            )
            for record, vector in zip(records, vectors, strict=True)
        ]
        for start in range(0, len(points), _BATCH_SIZE):
            await self._client.upsert(
                collection_name=self._collection,
                points=points[start : start + _BATCH_SIZE],
            )

    async def search(self, vector: list[float], limit: int) -> list[SearchHit]:
        response = await self._client.query_points(
            collection_name=self._collection,
            query=vector,
            limit=limit,
            with_payload=True,
        )
        return [_to_hit(point) for point in response.points]

    async def delete_document(self, document_id: uuid.UUID) -> None:
        await self._client.delete(
            collection_name=self._collection,
            points_selector=FilterSelector(
                filter=Filter(
                    must=[
                        FieldCondition(
                            key="document_id", match=MatchValue(value=str(document_id))
                        )
                    ]
                )
            ),
        )