import asyncio
import uuid

from qdrant_client import AsyncQdrantClient
from redis.asyncio import Redis

from app.core.config import get_settings
from app.embeddings.fastembed_embedder import FastEmbedEmbedder
from app.llm.openai_compatible import OpenAICompatibleLLM
from app.services.memory_service import RedisChatMemory
from app.services.rag_service import RagService
from app.vectorstore.base import ChunkRecord
from app.vectorstore.qdrant_store import QdrantVectorStore

SESSION_ID = "smoke-rag"


async def main() -> None:
    settings = get_settings()
    embedder = FastEmbedEmbedder(settings.embedding_model, settings.embedding_dimension)
    qdrant = AsyncQdrantClient(url=settings.qdrant_url)
    store = QdrantVectorStore(qdrant, "smoke_rag")
    await store.ensure_collection(embedder.dimension)
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    memory = RedisChatMemory(
        redis, settings.chat_history_max_messages, settings.chat_history_ttl_seconds
    )
    llm = OpenAICompatibleLLM(
        settings.llm_api_key.get_secret_value(), settings.llm_base_url, settings.llm_model
    )

    document_id = uuid.uuid4()
    texts = [
        "Employees receive 24 days of paid annual leave per year.",
        "Up to 5 unused leave days may be carried over into the next year.",
        "The office is closed on public holidays.",
        "Remote work is allowed on Fridays.",
    ]
    records = [ChunkRecord(document_id, i, t, "policy.txt") for i, t in enumerate(texts)]
    await store.upsert_chunks(records, await embedder.embed_documents(texts))
    await memory.clear(SESSION_ID)

    rag = RagService(
        embedder, store, llm, memory, settings.rag_top_k, settings.rag_min_score
    )
    for question in (
        "How many days of annual leave do employees get?",
        "And how many of those can I carry over?",
    ):
        result = await rag.answer(SESSION_ID, question)
        print(f"\nQ: {question}\nA: {result.answer}")
        for source in result.sources:
            print(f"   source: {source.filename} #{source.chunk_index} ({source.score:.2f})")

    await memory.clear(SESSION_ID)
    await store.delete_document(document_id)
    await llm.aclose()
    await redis.aclose()
    await qdrant.close()


if __name__ == "__main__":
    asyncio.run(main())