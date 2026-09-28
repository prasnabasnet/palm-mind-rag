from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from qdrant_client import AsyncQdrantClient

from app.core.config import get_settings
from app.embeddings.fastembed_embedder import FastEmbedEmbedder
from app.vectorstore.qdrant_store import QdrantVectorStore


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    embedder = FastEmbedEmbedder(settings.embedding_model, settings.embedding_dimension)
    client = AsyncQdrantClient(url=settings.qdrant_url)
    store = QdrantVectorStore(client, settings.qdrant_collection)
    await store.ensure_collection(embedder.dimension)

    app.state.embedder = embedder
    app.state.vector_store = store
    yield
    await client.close()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "environment": settings.environment}

    return app


app = create_app()