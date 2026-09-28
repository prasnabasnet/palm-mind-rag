import asyncio
import uuid

from qdrant_client import AsyncQdrantClient

from app.core.config import get_settings
from app.embeddings.fastembed_embedder import FastEmbedEmbedder
from app.vectorstore.base import ChunkRecord
from app.vectorstore.qdrant_store import QdrantVectorStore


async def main() -> None:
    settings = get_settings()
    embedder = FastEmbedEmbedder(settings.embedding_model, settings.embedding_dimension)
    client = AsyncQdrantClient(url=settings.qdrant_url)
    store = QdrantVectorStore(client, "smoke_test")
    await store.ensure_collection(embedder.dimension)

    document_id = uuid.uuid4()
    texts = [
        "To reset your password, open Settings and choose Security.",
        "Our office is closed on public holidays.",
        "Invoices are emailed on the first day of each month.",
    ]
    records = [
        ChunkRecord(document_id, i, text, "smoke.txt") for i, text in enumerate(texts)
    ]
    await store.upsert_chunks(records, await embedder.embed_documents(texts))

    query_vector = await embedder.embed_query("How do I change my password?")
    for hit in await store.search(query_vector, limit=2):
        print(f"{hit.score:.3f}  {hit.text}")

    await store.delete_document(document_id)
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())