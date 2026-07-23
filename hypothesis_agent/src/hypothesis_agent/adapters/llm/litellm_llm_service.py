"""LLMService backed by the `litellm` package: one unified `model` string
routes to whatever provider (or self-hosted LiteLLM proxy) `api_base` points
at, using a single `api_key`. This is the adapter meant for local/testing use
with a LiteLLM key — see .env.example for the three env vars it reads.

Observability: if LANGFUSE_PUBLIC_KEY/LANGFUSE_SECRET_KEY are set (see
.env.example), every acompletion() call below is traced to Langfuse via
litellm's built-in callback — litellm reads LANGFUSE_PUBLIC_KEY/
LANGFUSE_SECRET_KEY/LANGFUSE_HOST from the environment itself. Callers group
related calls into one Langfuse session by setting
`LLMRequest.metadata["session_id"]` (see reasoning/observability.py) — that
dict is forwarded to litellm's `metadata=` kwarg below unchanged, which is
the convention its Langfuse integration reads session_id/trace_name/etc
from. insight_pipeline reuses this same LiteLLMService instance, so its
calls are covered too, with zero changes on that side."""

from __future__ import annotations

import json
import os
from typing import TypeVar

from pydantic import BaseModel

from hypothesis_agent.contracts.llm import LLMRequest, LLMResponse
from hypothesis_agent.ports.llm_service import LLMService

T = TypeVar("T", bound=BaseModel)

# litellm's own model-name convention for OpenAI's cheapest general-purpose
# chat model at the time this was written. Override via config/env — this is
# a "good default for testing," not a hardcoded requirement.
_DEFAULT_MODEL = "gpt-4.1-nano"


class LiteLLMService(LLMService):
    def __init__(
        self,
        model: str = _DEFAULT_MODEL,
        api_key: str | None = None,
        api_base: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        try:
            import litellm
        except ImportError as exc:
            raise ImportError(
                "LiteLLMService requires the 'litellm' package: install hypothesis_agent[llm-litellm]"
            ) from exc
        # With a custom api_base, litellm can't always infer the provider from
        # the model name alone ("LLM Provider NOT provided" otherwise) — an
        # unprefixed model talking to a custom base is assumed OpenAI-API-shaped
        # (true for a LiteLLM proxy, which is the documented use case here).
        # An already-prefixed model (contains "/") is left untouched.
        self._model = model if "/" in model else f"openai/{model}"
        self._api_key = api_key
        self._api_base = api_base
        self._timeout = timeout
        # Different models behind the same gateway support different params
        # (e.g. some GPT-5-family models reject temperature != 1). Drop
        # whatever a given model doesn't support instead of failing the call.
        litellm.drop_params = True
        if os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY"):
            litellm.success_callback = ["langfuse"]
            litellm.failure_callback = ["langfuse"]
        self._litellm = litellm

    async def complete(self, request: LLMRequest) -> LLMResponse:
        response = await self._litellm.acompletion(
            model=self._model,
            messages=[m.model_dump() for m in request.messages],
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            api_key=self._api_key,
            api_base=self._api_base,
            timeout=self._timeout,
            metadata=request.metadata or None,
        )
        content = response.choices[0].message.content or ""
        return LLMResponse(content=content, raw=response.model_dump())

    async def complete_structured(self, request: LLMRequest, schema: type[T]) -> T:
        response = await self._litellm.acompletion(
            model=self._model,
            messages=[m.model_dump() for m in request.messages],
            temperature=request.temperature,
            response_format=schema,
            api_key=self._api_key,
            api_base=self._api_base,
            timeout=self._timeout,
            metadata=request.metadata or None,
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError(
                f"LiteLLM structured completion for schema {schema.__name__} returned empty content"
            )
        try:
            return schema.model_validate(json.loads(content))
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError(
                f"LiteLLM response for schema {schema.__name__} was not valid JSON matching "
                f"the schema: {content[:300]!r}"
            ) from exc
