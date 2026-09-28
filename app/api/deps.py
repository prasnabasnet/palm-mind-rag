from typing import Annotated, cast

from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.embeddings.base import Embedder
from app.repositories.document_repository import DocumentRepository
from app.services.ingestion_service import IngestionService
from app.services.memory_service import ChatMemory, RedisChatMemory
from app.vectorstore.base import VectorStore

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_embedder(request: Request) -> Embedder:
    return cast(Embedder, request.app.state.embedder)


def get_vector_store(request: Request) -> VectorStore:
    return cast(VectorStore, request.app.state.vector_store)


def get_redis(request: Request) -> Redis:
    return cast(Redis, request.app.state.redis)


def get_ingestion_service(
    session: SessionDep,
    settings: SettingsDep,
    embedder: Annotated[Embedder, Depends(get_embedder)],
    vector_store: Annotated[VectorStore, Depends(get_vector_store)],
) -> IngestionService:
    return IngestionService(
        DocumentRepository(session), embedder, vector_store, settings.max_upload_bytes
    )


def get_chat_memory(
    redis: Annotated[Redis, Depends(get_redis)],
    settings: SettingsDep,
) -> ChatMemory:
    return RedisChatMemory(
        redis, settings.chat_history_max_messages, settings.chat_history_ttl_seconds
    )


IngestionServiceDep = Annotated[IngestionService, Depends(get_ingestion_service)]
ChatMemoryDep = Annotated[ChatMemory, Depends(get_chat_memory)]