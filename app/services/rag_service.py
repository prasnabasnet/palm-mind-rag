import logging
from dataclasses import dataclass
from typing import Literal

from app.core.enums import MessageRole
from app.embeddings.base import Embedder
from app.llm.base import ChatLLM, LLMMessage
from app.schemas.chat import ChatMessage, SourceReference
from app.services.memory_service import ChatMemory
from app.services.prompts import CONDENSE_SYSTEM_PROMPT, NO_CONTEXT, RAG_SYSTEM_PROMPT
from app.vectorstore.base import SearchHit, VectorStore

logger = logging.getLogger(__name__)

_CONDENSE_HISTORY_MESSAGES = 6


@dataclass(frozen=True, slots=True)
class RagAnswer:
    answer: str
    sources: list[SourceReference]


def _to_llm_message(message: ChatMessage) -> LLMMessage:
    role: Literal["user", "assistant"] = (
        "user" if message.role == MessageRole.USER else "assistant"
    )
    return {"role": role, "content": message.content}


def _format_context(hits: list[SearchHit]) -> str:
    if not hits:
        return NO_CONTEXT
    return "\n\n".join(
        f"[{number}] (from {hit.filename})\n{hit.text}"
        for number, hit in enumerate(hits, start=1)
    )


class RagService:
    """Retrieval-augmented answering, written out step by step (no chain abstractions)."""

    def __init__(
        self,
        embedder: Embedder,
        vector_store: VectorStore,
        llm: ChatLLM,
        memory: ChatMemory,
        top_k: int,
        min_score: float,
    ) -> None:
        self._embedder = embedder
        self._vector_store = vector_store
        self._llm = llm
        self._memory = memory
        self._top_k = top_k
        self._min_score = min_score

    async def answer(self, session_id: str, question: str) -> RagAnswer:
        history = await self._memory.get_history(session_id)
        search_query = await self._standalone_question(history, question)
        hits = await self._retrieve(search_query)

        messages = self._build_messages(history, question, hits)
        answer = await self._llm.complete(messages)

        await self._memory.append(
            session_id,
            [
                ChatMessage(role=MessageRole.USER, content=question),
                ChatMessage(role=MessageRole.ASSISTANT, content=answer),
            ],
        )
        return RagAnswer(
            answer=answer,
            sources=[
                SourceReference(
                    document_id=hit.document_id,
                    filename=hit.filename,
                    chunk_index=hit.chunk_index,
                    score=hit.score,
                )
                for hit in hits
            ],
        )

    async def _standalone_question(self, history: list[ChatMessage], question: str) -> str:
        if not history:
            return question
        transcript = "\n".join(
            f"{'User' if m.role == MessageRole.USER else 'Assistant'}: {m.content}"
            for m in history[-_CONDENSE_HISTORY_MESSAGES:]
        )
        prompt = (
            f"Conversation so far:\n{transcript}\n\n"
            f"Latest message: {question}\n\nStandalone question:"
        )
        rewritten = await self._llm.complete(
            [
                {"role": "system", "content": CONDENSE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )
        return rewritten or question

    async def _retrieve(self, query: str) -> list[SearchHit]:
        vector = await self._embedder.embed_query(query)
        hits = await self._vector_store.search(vector, self._top_k)
        return [hit for hit in hits if hit.score >= self._min_score]

    @staticmethod
    def _build_messages(
        history: list[ChatMessage], question: str, hits: list[SearchHit]
    ) -> list[LLMMessage]:
        messages: list[LLMMessage] = [
            {"role": "system", "content": RAG_SYSTEM_PROMPT.format(context=_format_context(hits))}
        ]
        messages.extend(_to_llm_message(m) for m in history)
        messages.append({"role": "user", "content": question})
        return messages