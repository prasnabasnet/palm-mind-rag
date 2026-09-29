import uuid

from app.core.enums import MessageRole
from app.llm.base import LLMMessage
from app.schemas.chat import ChatMessage
from app.services.prompts import NO_CONTEXT
from app.services.rag_service import RagService
from app.vectorstore.base import ChunkRecord, SearchHit


class RecordingLLM:
    def __init__(self, replies: list[str]) -> None:
        self._replies = list(replies)
        self.calls: list[list[LLMMessage]] = []

    async def complete(
        self, messages: list[LLMMessage], *, json_mode: bool = False, temperature: float = 0.2
    ) -> str:
        self.calls.append(messages)
        return self._replies.pop(0)


class FakeEmbedder:
    dimension = 3

    def __init__(self) -> None:
        self.queries: list[str] = []

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in texts]

    async def embed_query(self, text: str) -> list[float]:
        self.queries.append(text)
        return [0.1, 0.2, 0.3]


class FakeVectorStore:
    def __init__(self, hits: list[SearchHit]) -> None:
        self._hits = hits

    async def ensure_collection(self, dimension: int) -> None:
        return None

    async def upsert_chunks(
        self, records: list[ChunkRecord], vectors: list[list[float]]
    ) -> None:
        return None

    async def search(self, vector: list[float], limit: int) -> list[SearchHit]:
        return self._hits[:limit]

    async def delete_document(self, document_id: uuid.UUID) -> None:
        return None


class FakeMemory:
    def __init__(self, history: list[ChatMessage] | None = None) -> None:
        self.messages: list[ChatMessage] = list(history or [])

    async def append(self, session_id: str, messages: list[ChatMessage]) -> None:
        self.messages.extend(messages)

    async def get_history(self, session_id: str) -> list[ChatMessage]:
        return list(self.messages)

    async def clear(self, session_id: str) -> None:
        self.messages.clear()


def make_hit(text: str, score: float) -> SearchHit:
    return SearchHit(
        document_id=uuid.uuid4(), chunk_index=0, text=text, filename="policy.txt", score=score
    )


def make_service(
    llm: RecordingLLM,
    memory: FakeMemory,
    hits: list[SearchHit],
    embedder: FakeEmbedder | None = None,
) -> RagService:
    return RagService(
        embedder=embedder or FakeEmbedder(),
        vector_store=FakeVectorStore(hits),
        llm=llm,
        memory=memory,
        top_k=4,
        min_score=0.35,
    )


async def test_first_turn_grounds_answer_in_retrieved_chunk() -> None:
    llm = RecordingLLM(["You get 24 days."])
    memory = FakeMemory()
    service = make_service(llm, memory, [make_hit("Employees receive 24 days of leave.", 0.8)])

    result = await service.answer("s1", "How much leave do I get?")

    assert result.answer == "You get 24 days."
    assert len(llm.calls) == 1
    assert "Employees receive 24 days of leave." in llm.calls[0][0]["content"]
    assert llm.calls[0][-1] == {"role": "user", "content": "How much leave do I get?"}
    assert [m.role for m in memory.messages] == [MessageRole.USER, MessageRole.ASSISTANT]
    assert len(result.sources) == 1


async def test_low_score_chunks_are_dropped() -> None:
    llm = RecordingLLM(["I could not find that."])
    service = make_service(llm, FakeMemory(), [make_hit("Unrelated text.", 0.1)])

    result = await service.answer("s1", "What is the meaning of life?")

    assert result.sources == []
    assert NO_CONTEXT in llm.calls[0][0]["content"]


async def test_follow_up_is_rewritten_before_retrieval() -> None:
    history = [
        ChatMessage(role=MessageRole.USER, content="How much leave do I get?"),
        ChatMessage(role=MessageRole.ASSISTANT, content="You get 24 days."),
    ]
    llm = RecordingLLM(["How many leave days can be carried over?", "Five days."])
    embedder = FakeEmbedder()
    service = make_service(
        llm, FakeMemory(history), [make_hit("Up to 5 days carry over.", 0.8)], embedder
    )

    result = await service.answer("s1", "And how many can I carry over?")

    assert embedder.queries == ["How many leave days can be carried over?"]
    assert len(llm.calls) == 2
    assert [m["role"] for m in llm.calls[1]] == ["system", "user", "assistant", "user"]
    assert result.answer == "Five days."