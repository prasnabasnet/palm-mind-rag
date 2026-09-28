import logging
from typing import Protocol

from pydantic import ValidationError
from redis.asyncio import Redis

from app.schemas.chat import ChatMessage

logger = logging.getLogger(__name__)


class ChatMemory(Protocol):
    async def append(self, session_id: str, messages: list[ChatMessage]) -> None: ...

    async def get_history(self, session_id: str) -> list[ChatMessage]: ...

    async def clear(self, session_id: str) -> None: ...


class RedisChatMemory:

    def __init__(self, client: Redis, max_messages: int, ttl_seconds: int) -> None:
        self._client = client
        self._max_messages = max_messages
        self._ttl_seconds = ttl_seconds

    @staticmethod
    def _key(session_id: str) -> str:
        return f"chat:{session_id}:history"

    async def append(self, session_id: str, messages: list[ChatMessage]) -> None:
        if not messages:
            return
        key = self._key(session_id)
        async with self._client.pipeline(transaction=True) as pipe:
            pipe.rpush(key, *(message.model_dump_json() for message in messages))
            pipe.ltrim(key, -self._max_messages, -1)
            pipe.expire(key, self._ttl_seconds)
            await pipe.execute()

    async def get_history(self, session_id: str) -> list[ChatMessage]:
        async with self._client.pipeline(transaction=False) as pipe:
            pipe.lrange(self._key(session_id), 0, -1)
            results = await pipe.execute()
        raw_items: list[str] = results[0]

        history: list[ChatMessage] = []
        for item in raw_items:
            try:
                history.append(ChatMessage.model_validate_json(item))
            except ValidationError:
                logger.warning("Skipping malformed chat message in session %s", session_id)
        return history

    async def clear(self, session_id: str) -> None:
        await self._client.delete(self._key(session_id))