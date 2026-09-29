from typing import Annotated, cast

from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.embeddings.base import Embedder
from app.llm.base import ChatLLM
from app.repositories.booking_repository import BookingRepository
from app.repositories.document_repository import DocumentRepository
from app.services.booking_service import BookingService
from app.services.chat_service import ChatService
from app.services.ingestion_service import IngestionService
from app.services.memory_service import ChatMemory, RedisChatMemory
from app.services.rag_service import RagService
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
def get_llm(request: Request) -> ChatLLM:
    return cast(ChatLLM, request.app.state.llm)


def get_rag_service(
    embedder: Annotated[Embedder, Depends(get_embedder)],
    vector_store: Annotated[VectorStore, Depends(get_vector_store)],
    llm: Annotated[ChatLLM, Depends(get_llm)],
    memory: Annotated[ChatMemory, Depends(get_chat_memory)],
    settings: SettingsDep,
) -> RagService:
    return RagService(
        embedder, vector_store, llm, memory, settings.rag_top_k, settings.rag_min_score
    )

def get_booking_service(
    session: SessionDep, llm: Annotated[ChatLLM, Depends(get_llm)]
) -> BookingService:
    return BookingService(llm, BookingRepository(session))


def get_chat_service(
    rag_service: Annotated[RagService, Depends(get_rag_service)],
    booking_service: Annotated[BookingService, Depends(get_booking_service)],
    memory: Annotated[ChatMemory, Depends(get_chat_memory)],
) -> ChatService:
    return ChatService(rag_service, booking_service, memory)


ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]

RagServiceDep = Annotated[RagService, Depends(get_rag_service)]

IngestionServiceDep = Annotated[IngestionService, Depends(get_ingestion_service)]
ChatMemoryDep = Annotated[ChatMemory, Depends(get_chat_memory)]