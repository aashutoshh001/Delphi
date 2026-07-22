"""Opt-in tests against real backends. Skipped unless RUN_LIVE_TESTS=1 and
the relevant API key is present — never run by default, never in CI without
explicit opt-in, since they cost money and need network access."""

import os

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LIVE_TESTS") != "1",
    reason="set RUN_LIVE_TESTS=1 to run tests against real LLM/embedding backends",
)


@pytest.mark.skipif(not os.environ.get("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")
async def test_openai_llm_service_completes_structured_output():
    from pydantic import BaseModel

    from hypothesis_agent.adapters.llm.openai_llm_service import OpenAILLMService
    from hypothesis_agent.contracts.llm import LLMMessage, LLMRequest

    class _Answer(BaseModel):
        value: int

    llm = OpenAILLMService()
    request = LLMRequest(messages=[LLMMessage(role="user", content="Reply with value=42.")])
    result = await llm.complete_structured(request, _Answer)
    assert result.value == 42


@pytest.mark.skipif(not os.environ.get("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")
async def test_openai_embedding_service_returns_a_vector():
    from hypothesis_agent.adapters.embeddings.openai_embedding_service import (
        OpenAIEmbeddingService,
    )

    service = OpenAIEmbeddingService()
    embedding = await service.embed("burnout and resilience")
    assert len(embedding) > 0


@pytest.mark.skipif(not os.environ.get("LITELLM_API_KEY"), reason="LITELLM_API_KEY not set")
async def test_litellm_service_completes_structured_output():
    from pydantic import BaseModel

    from hypothesis_agent.adapters.llm.litellm_llm_service import LiteLLMService
    from hypothesis_agent.contracts.llm import LLMMessage, LLMRequest

    class _Answer(BaseModel):
        value: int

    llm = LiteLLMService(
        api_key=os.environ["LITELLM_API_KEY"],
        api_base=os.environ.get("LITELLM_API_BASE"),
    )
    request = LLMRequest(messages=[LLMMessage(role="user", content="Reply with value=42.")])
    result = await llm.complete_structured(request, _Answer)
    assert result.value == 42


async def test_full_search_loop_with_litellm_backend_end_to_end():
    if not os.environ.get("LITELLM_API_KEY"):
        pytest.skip("LITELLM_API_KEY not set")

    from hypothesis_agent.agent import HypothesisAgent
    from hypothesis_agent.config.settings import AgentConfig
    from hypothesis_agent.contracts.organization import (
        EmployeeDataLandscape,
        OrganizationProfile,
    )
    from hypothesis_agent.di.container import build_dependencies

    config = AgentConfig.load()
    config.backends.llm = "litellm"
    config.search.max_iterations = 2
    deps = build_dependencies(config)
    deps.organization_repository.add(OrganizationProfile(organization_id="live-org"))
    deps.employee_repository.add(EmployeeDataLandscape(organization_id="live-org"))

    agent = HypothesisAgent(deps)
    package = await agent.discover("live-org")
    assert package.hypothesis_statement
