from pydantic import BaseModel

from hypothesis_agent.adapters.llm.mock_llm_service import MockLLMService
from hypothesis_agent.contracts.llm import LLMMessage, LLMRequest


class _Schema(BaseModel):
    value: float
    rationale: str
    tags: list[str]


async def test_complete_structured_returns_valid_instance():
    llm = MockLLMService()
    request = LLMRequest(messages=[LLMMessage(role="user", content="score this hypothesis")])
    result = await llm.complete_structured(request, _Schema)
    assert isinstance(result, _Schema)
    assert isinstance(result.tags, list)


async def test_complete_structured_is_deterministic_for_same_input():
    llm = MockLLMService()
    request = LLMRequest(messages=[LLMMessage(role="user", content="same prompt")])
    first = await llm.complete_structured(request, _Schema)
    second = await llm.complete_structured(request, _Schema)
    assert first == second


async def test_complete_structured_differs_for_different_input():
    llm = MockLLMService()
    a = await llm.complete_structured(
        LLMRequest(messages=[LLMMessage(role="user", content="prompt A")]), _Schema
    )
    b = await llm.complete_structured(
        LLMRequest(messages=[LLMMessage(role="user", content="prompt B")]), _Schema
    )
    assert a != b
