"""LLM-call contracts. Every prompt/response in the reasoning engine flows
through these, never raw strings-in-dicts-out."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class LLMMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class LLMRequest(BaseModel):
    messages: list[LLMMessage]
    temperature: float = 0.7
    max_tokens: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    content: str
    raw: dict[str, Any] = Field(default_factory=dict)
