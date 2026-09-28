from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from qdrant_client import AsyncQdrantClient
from redis.asyncio import Redis

from app.api.errors import register_exception_handlers
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.embeddings.fastembed_embedder import FastEmbedEmbedder
from app.vectorstore.qdrant_store import QdrantVectorStore


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    embedder = FastEmbedEmbedder(settings.embedding_model, settings.embedding_dimension)
    qdrant_client = AsyncQdrantClient(url=settings.qdrant_url)
    store = QdrantVectorStore(qdrant_client, settings.qdrant_collection)
    await store.ensure_collection(embedder.dimension)
    redis_client = Redis.from_url(settings.redis_url, decode_responses=True)

    app.state.embedder = embedder
    app.state.vector_store = store
    app.state.redis = redis_client
    yield
    await redis_client.aclose()
    await qdrant_client.close()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    register_exception_handlers(app)
    app.include_router(api_router)

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "environment": settings.environment}

    return app


app = create_app()