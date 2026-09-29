from typing import cast

import openai
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from app.core.exceptions import LLMError
from app.llm.base import LLMMessage


class OpenAICompatibleLLM:
    """Chat client for any provider that speaks the OpenAI API (Groq, OpenAI, Gemini...)."""

    def __init__(
        self, api_key: str, base_url: str, model: str, timeout_seconds: float = 60.0
    ) -> None:
        self._client = AsyncOpenAI(
            api_key=api_key, base_url=base_url, timeout=timeout_seconds, max_retries=2
        )
        self._model = model

    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        json_mode: bool = False,
        temperature: float = 0.2,
    ) -> str:
        payload = cast(list[ChatCompletionMessageParam], messages)
        try:
            if json_mode:
                response = await self._client.chat.completions.create(
                    model=self._model,
                    messages=payload,
                    temperature=temperature,
                    response_format={"type": "json_object"},
                )
            else:
                response = await self._client.chat.completions.create(
                    model=self._model,
                    messages=payload,
                    temperature=temperature,
                )
        except openai.OpenAIError as exc:
            raise LLMError("The language model request failed.") from exc

        if not response.choices:
            raise LLMError("The language model returned no choices.")
        return (response.choices[0].message.content or "").strip()

    async def aclose(self) -> None:
        await self._client.close()