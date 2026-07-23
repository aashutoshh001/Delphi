"""Deterministic, offline LLMService. Fabricates structurally-valid responses
from the seed text (schema field values are derived from a hash of the
prompt, not randomness across runs) so `examples/run_local_demo.py` and the
test suite run with no network access and no API key."""

from __future__ import annotations

import hashlib
import random
import types
import typing
from typing import TypeVar, get_args, get_origin

from pydantic import BaseModel

from hypothesis_agent.contracts.llm import LLMRequest, LLMResponse
from hypothesis_agent.ports.llm_service import LLMService

T = TypeVar("T", bound=BaseModel)

_WORDS = [
    "organizational", "hidden", "mechanism", "performance", "resilience",
    "engagement", "leadership", "communication", "attrition", "learning",
    "competency", "signal", "structural", "strategic", "latent",
]

# A uniform coin-flip per bool field is realistic for nothing: a real critic
# rarely calls a fresh candidate obvious/duplicate, and rarely calls it
# non-actionable. Bias fabricated critique-shaped fields accordingly so mock
# runs behave like a plausible-if-generic LLM rather than an adversarial one.
_BOOL_TRUE_PROBABILITY = {
    "is_obvious": 0.15,
    "similar_to_prior": 0.15,
    "creates_actionable_decision": 0.85,
    "reveals_hidden_mechanism": 0.85,
    "downstream_feasible": 0.85,
}


def _rng_for(seed_text: str, salt: str) -> random.Random:
    digest = hashlib.sha256(f"{seed_text}::{salt}".encode()).hexdigest()
    return random.Random(digest)


def _fabricate_str(rng: random.Random, field_name: str) -> str:
    words = [rng.choice(_WORDS) for _ in range(rng.randint(6, 14))]
    return f"[mock:{field_name}] " + " ".join(words) + "."


def _fabricate_value(annotation: object, field_name: str, rng: random.Random) -> object:
    origin = get_origin(annotation)
    if origin is typing.Union or origin is types.UnionType:
        args = [a for a in get_args(annotation) if a is not type(None)]
        return _fabricate_value(args[0], field_name, rng) if args else None
    if origin is typing.Literal:
        choices = get_args(annotation)
        return rng.choice(choices) if choices else _fabricate_str(rng, field_name)
    if origin in (list, typing.List):
        (inner,) = get_args(annotation) or (str,)
        return [_fabricate_value(inner, field_name, rng) for _ in range(rng.randint(1, 2))]
    if origin is tuple:
        inner_types = get_args(annotation) or (float, float)
        return tuple(_fabricate_value(t, field_name, rng) for t in inner_types)
    if origin in (dict, typing.Dict):
        return {}
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        nested_values = {
            name: _fabricate_value(field.annotation, name, rng)
            for name, field in annotation.model_fields.items()
        }
        return annotation.model_validate(nested_values)
    if annotation is bool:
        return rng.random() < _BOOL_TRUE_PROBABILITY.get(field_name, 0.5)
    if annotation is float:
        return round(rng.uniform(0.3, 0.9), 3)
    if annotation is int:
        return rng.randint(0, 10)
    if annotation is str:
        return _fabricate_str(rng, field_name)
    return _fabricate_str(rng, field_name)


class MockLLMService(LLMService):
    async def complete(self, request: LLMRequest) -> LLMResponse:
        seed_text = request.messages[-1].content if request.messages else ""
        rng = _rng_for(seed_text, "complete")
        return LLMResponse(content=_fabricate_str(rng, "content"))

    async def complete_structured(self, request: LLMRequest, schema: type[T]) -> T:
        seed_text = "||".join(m.content for m in request.messages)
        rng = _rng_for(seed_text, schema.__name__)
        values: dict[str, object] = {}
        for name, field in schema.model_fields.items():
            values[name] = _fabricate_value(field.annotation, name, rng)
        return schema.model_validate(values)
