from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from hypothesis_agent.contracts.llm import LLMRequest, LLMResponse
from hypothesis_agent.ports.llm_service import LLMService

T = TypeVar("T", bound=BaseModel)


class OpenAILLMService(LLMService):
    """Real LLM backend. `openai` is an optional extra
    (`hypothesis_agent[llm-openai]`); importing it lazily keeps the core
    package installable with zero third-party LLM SDKs."""

    def __init__(
        self,
        model: str = "gpt-4.1-mini",
        api_key: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise ImportError(
                "OpenAILLMService requires the 'openai' package: "
                "install hypothesis_agent[llm-openai]"
            ) from exc
        self._model = model
        self._client = AsyncOpenAI(api_key=api_key, timeout=timeout)

    async def complete(self, request: LLMRequest) -> LLMResponse:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[m.model_dump() for m in request.messages],
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        content = response.choices[0].message.content or ""
        return LLMResponse(content=content, raw=response.model_dump())

    async def complete_structured(self, request: LLMRequest, schema: type[T]) -> T:
        response = await self._client.chat.completions.parse(
            model=self._model,
            messages=[m.model_dump() for m in request.messages],
            temperature=request.temperature,
            response_format=schema,
        )
        parsed = response.choices[0].message.parsed
        if parsed is None:
            raise ValueError(
                f"OpenAI structured completion for schema {schema.__name__} returned no parsed content"
            )
        return parsed
