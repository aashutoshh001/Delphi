"""InvestigationSeed is opt-in and off by default; when enabled it's
populated with a plausible structure, offline via MockLLMService."""

from hypothesis_agent.agent import HypothesisAgent
from hypothesis_agent.config.settings import AgentConfig
from hypothesis_agent.contracts.organization import EmployeeDataLandscape, OrganizationProfile
from hypothesis_agent.di.container import build_dependencies


async def _run(generate_seed: bool):
    config = AgentConfig.load()
    # Force offline backends regardless of a local .env's real-endpoint
    # config (e.g. backends.llm=litellm for server/production use) — this
    # test must stay fast/deterministic/network-free like the rest of the suite.
    config.backends.llm = "mock"
    config.backends.embedding = "hash"
    config.search.max_iterations = 3
    config.search.random_seed = 11
    config.search.generate_investigation_seed = generate_seed
    deps = build_dependencies(config)
    deps.organization_repository.add(OrganizationProfile(organization_id="seed-org"))
    deps.employee_repository.add(EmployeeDataLandscape(organization_id="seed-org"))
    agent = HypothesisAgent(deps)
    return await agent.discover("seed-org")


async def test_investigation_seed_absent_by_default():
    package = await _run(generate_seed=False)
    assert package.investigation_seed is None


async def test_investigation_seed_populated_when_enabled():
    package = await _run(generate_seed=True)
    assert package.investigation_seed is not None
    assert isinstance(package.investigation_seed.expected_investigation_objectives, list)
