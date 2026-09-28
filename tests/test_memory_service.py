import pytest
from fakeredis import FakeAsyncRedis, FakeServer

from app.core.enums import MessageRole
from app.schemas.chat import ChatMessage
from app.services.memory_service import RedisChatMemory


@pytest.fixture
def redis_client() -> FakeAsyncRedis:
    return FakeAsyncRedis(server=FakeServer(), decode_responses=True)


def make_memory(client: FakeAsyncRedis, max_messages: int = 4) -> RedisChatMemory:
    return RedisChatMemory(client, max_messages=max_messages, ttl_seconds=60)


def pair(n: int) -> list[ChatMessage]:
    return [
        ChatMessage(role=MessageRole.USER, content=f"question {n}"),
        ChatMessage(role=MessageRole.ASSISTANT, content=f"answer {n}"),
    ]


async def test_history_round_trips_in_order(redis_client: FakeAsyncRedis) -> None:
    memory = make_memory(redis_client)
    await memory.append("s1", pair(1))

    history = await memory.get_history("s1")

    assert [m.content for m in history] == ["question 1", "answer 1"]
    assert history[0].role == MessageRole.USER


async def test_history_is_trimmed_to_window(redis_client: FakeAsyncRedis) -> None:
    memory = make_memory(redis_client, max_messages=4)
    for n in range(1, 4):
        await memory.append("s1", pair(n))

    history = await memory.get_history("s1")

    assert [m.content for m in history] == [
        "question 2", "answer 2", "question 3", "answer 3",
    ]


async def test_sessions_are_isolated(redis_client: FakeAsyncRedis) -> None:
    memory = make_memory(redis_client)
    await memory.append("a", pair(1))

    assert await memory.get_history("b") == []


async def test_append_sets_expiry(redis_client: FakeAsyncRedis) -> None:
    memory = make_memory(redis_client)
    await memory.append("s1", pair(1))

    ttl = await redis_client.ttl("chat:s1:history")

    assert 0 < ttl <= 60


async def test_clear_removes_history(redis_client: FakeAsyncRedis) -> None:
    memory = make_memory(redis_client)
    await memory.append("s1", pair(1))
    await memory.clear("s1")

    assert await memory.get_history("s1") == []