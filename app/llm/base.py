from typing import Literal, Protocol, TypedDict


class LLMMessage(TypedDict):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatLLM(Protocol):
    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        json_mode: bool = False,
        temperature: float = 0.2,
    ) -> str: ...