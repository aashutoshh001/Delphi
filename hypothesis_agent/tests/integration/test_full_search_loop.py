"""End-to-end graph run using only in-memory/offline adapters — no network,
no API key. Mirrors examples/run_local_demo.py."""

from hypothesis_agent.agent import HypothesisAgent
from hypothesis_agent.config.settings import AgentConfig
from hypothesis_agent.contracts.hypothesis import HypothesisPackage
from hypothesis_agent.contracts.organization import (
    AttributeField,
    EmployeeDataLandscape,
    OrganizationProfile,
)
from hypothesis_agent.di.container import build_dependencies


def _offline_config(**overrides) -> AgentConfig:
    """Forces the offline/deterministic backends explicitly, regardless of
    whatever HYPOTHESIS_AGENT__BACKENDS__LLM is set to in a local .env —
    these tests must never make a network call."""
    config = AgentConfig.load()
    config.backends.llm = "mock"
    config.backends.embedding = "hash"
    for key, value in overrides.items():
        setattr(config.search, key, value)
    return config


async def _run(max_iterations: int = 6, random_seed: int = 7) -> HypothesisPackage:
    config = _offline_config(max_iterations=max_iterations, random_seed=random_seed)
    deps = build_dependencies(config)

    deps.organization_repository.add(
        OrganizationProfile(organization_id="org-1", name="Org One", core_attributes={"industry": "retail"})
    )
    deps.employee_repository.add(
        EmployeeDataLandscape(
            organization_id="org-1",
            employee_count_estimate=500,
            available_fields=[
                AttributeField(name="burnout_index", category="burnout", coverage_ratio=0.7),
                AttributeField(name="performance_rating", category="performance", coverage_ratio=0.9),
            ],
        )
    )

    agent = HypothesisAgent(deps)
    return await agent.discover("org-1")


async def test_discover_returns_valid_package():
    package = await _run()
    assert package.organization_id == "org-1"
    assert package.hypothesis_statement
    assert 0.0 <= package.scorecard.composite <= 1.0
    assert package.search_stats.iterations_run <= 6


async def test_discover_respects_max_iterations_budget():
    package = await _run(max_iterations=5)
    assert package.search_stats.iterations_run <= 5


async def test_discover_explores_more_than_one_lens_within_a_few_iterations():
    package = await _run(max_iterations=6)
    assert len(package.search_stats.lenses_explored) >= 2


async def test_discover_persists_to_historical_memory():
    config = _offline_config(random_seed=7)
    deps = build_dependencies(config)
    deps.organization_repository.add(OrganizationProfile(organization_id="org-2"))
    deps.employee_repository.add(EmployeeDataLandscape(organization_id="org-2"))

    agent = HypothesisAgent(deps)
    await agent.discover("org-2")

    recent = await deps.historical_memory_repository.list_recent("org-2")
    assert len(recent) == 1
