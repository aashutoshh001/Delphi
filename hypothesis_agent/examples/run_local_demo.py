"""End-to-end demo with zero network access and zero config: in-memory
repositories, MockLLMService, HashEmbeddingService. Run with:

    python examples/run_local_demo.py
"""

from __future__ import annotations

import asyncio

from hypothesis_agent.agent import HypothesisAgent
from hypothesis_agent.config.settings import AgentConfig
from hypothesis_agent.contracts.organization import AttributeField, EmployeeDataLandscape, OrganizationProfile
from hypothesis_agent.di.container import build_dependencies


async def main() -> None:
    # Force the offline backends explicitly — this script promises zero
    # network access regardless of what a local .env otherwise configures
    # (e.g. a real backends.llm=litellm for the server/production use).
    config = AgentConfig.load()
    config.backends.llm = "mock"
    config.backends.embedding = "hash"
    deps = build_dependencies(config)

    deps.organization_repository.add(
        OrganizationProfile(
            organization_id="acme-labs",
            name="Acme Labs",
            core_attributes={
                "industry": "enterprise software",
                "headcount_band": "1000-5000",
                "structure": "matrixed, 6 business units",
                "business_goals": ["reduce regretted attrition", "scale engineering leadership bench"],
            },
        )
    )
    deps.employee_repository.add(
        EmployeeDataLandscape(
            organization_id="acme-labs",
            employee_count_estimate=3200,
            available_fields=[
                AttributeField(name="performance_rating", category="performance", data_type="ordinal", coverage_ratio=0.95),
                AttributeField(name="burnout_index", category="burnout", data_type="numeric", coverage_ratio=0.6),
                AttributeField(name="communication_competency", category="communication", data_type="numeric", coverage_ratio=0.7),
                AttributeField(name="tenure_months", category="tenure", data_type="numeric", coverage_ratio=1.0),
                AttributeField(name="leadership_competency", category="leadership", data_type="numeric", coverage_ratio=0.5),
                AttributeField(name="technical_competency", category="technical_competency", data_type="numeric", coverage_ratio=0.8),
                AttributeField(name="promotion_last_18mo", category="promotion", data_type="boolean", coverage_ratio=1.0),
            ],
        )
    )

    agent = HypothesisAgent(deps)
    package = await agent.discover("acme-labs")

    print("=" * 80)
    print(f"Lens: {package.business_lens}")
    print(f"Hypothesis: {package.hypothesis_statement}")
    print(f"Mechanism: {package.mechanism_explanation}")
    print(f"Composite score: {package.scorecard.composite:.3f}")
    print(f"Iterations run: {package.search_stats.iterations_run}")
    print(f"Lenses explored: {package.search_stats.lenses_explored}")
    print(f"Termination reason: {package.search_stats.termination_reason}")
    print(f"Downstream hints: {package.downstream_hints.suggested_analysis_types}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
