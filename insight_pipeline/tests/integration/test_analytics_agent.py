"""Analytics Agent against the real Book1_standardized.xlsx cohort — real
scipy statistics, not mocked, so this validates the whole plugin selection +
concurrent execution path against real data shapes (numeric OPQ domain
scores, categorical OPQ facet bands and MQ categories)."""

from pathlib import Path

import pytest

from insight_pipeline.adapters.employee_data.excel_repository import ExcelEmployeeDataRepository
from insight_pipeline.adapters.employee_data.handle_cache import InMemoryDatasetHandleCache
from insight_pipeline.agents.analytics.facade import AnalyticsAgent
from insight_pipeline.contracts.dataset import DatasetMetadata, RetrievalQuery, RetrievedDataset
from insight_pipeline.contracts.investigation import InvestigationPlan, PopulationSpec, VariableSpec
from insight_pipeline.plugins.analysis_methods import default_analysis_method_registry
from hypothesis_agent.contracts.organization import AttributeField

_XLSX_PATH = Path(__file__).parents[3] / "Book1_standardized.xlsx"

pytestmark = pytest.mark.skipif(not _XLSX_PATH.exists(), reason="Book1_standardized.xlsx not present")


async def _retrieve(cache, requested_fields):
    repo = ExcelEmployeeDataRepository(_XLSX_PATH, cache)
    handle = await repo.resolve(
        RetrievalQuery(organization_id="shl-sample-cohort", requested_fields=requested_fields)
    )
    return handle


def _field(name: str, category: str, data_type: str) -> AttributeField:
    return AttributeField(name=name, category=category, data_type=data_type, coverage_ratio=1.0)


async def test_analytics_agent_runs_correlation_regression_anova_chi_square():
    cache = InMemoryDatasetHandleCache()
    handle = await _retrieve(
        cache,
        ["4_personality", "7_personality", "1.1_personality", "MQ.E.1_cat"],
    )
    dataset = RetrievedDataset(
        investigation_plan_id="plan_test",
        handle=handle,
        metadata=DatasetMetadata(
            fields=[
                _field("4_personality", "opq_domain", "numeric"),
                _field("7_personality", "opq_domain", "numeric"),
                _field("1.1_personality", "opq_facet", "categorical"),
                _field("MQ.E.1_cat", "motivation_item", "categorical"),
            ]
        ),
    )
    plan = InvestigationPlan(
        id="plan_test",
        hypothesis_package_id="pkg_test",
        organization_id="shl-sample-cohort",
        target_population=PopulationSpec(description="all candidates"),
        variables_required=[
            VariableSpec(name="4_personality", role="independent", expected_type="numeric"),
            VariableSpec(name="7_personality", role="dependent", expected_type="numeric"),
            VariableSpec(name="1.1_personality", role="independent", expected_type="categorical"),
            VariableSpec(name="MQ.E.1_cat", role="control", expected_type="categorical"),
        ],
    )
    registry = default_analysis_method_registry(cache)
    agent = AnalyticsAgent(registry, max_methods=6)

    result = await agent.run(dataset, plan)

    methods = {r.method for r in result.methods_run}
    assert "correlation" in methods
    assert "simple_linear_regression" in methods
    assert "one_way_anova" in methods
    assert "chi_square_independence" in methods
    hypothesis_test_methods = {"correlation", "simple_linear_regression", "one_way_anova", "chi_square_independence"}
    for r in result.methods_run:
        if r.method in hypothesis_test_methods:
            assert r.p_value is not None, f"{r.method} produced no p_value"
        print(r.method, r.interpretation_notes)


async def test_analytics_agent_handles_no_applicable_methods_gracefully():
    cache = InMemoryDatasetHandleCache()
    handle = await _retrieve(cache, ["candidate_id"])
    dataset = RetrievedDataset(
        investigation_plan_id="plan_empty",
        handle=handle,
        metadata=DatasetMetadata(fields=[]),
    )
    plan = InvestigationPlan(
        hypothesis_package_id="pkg_test",
        organization_id="shl-sample-cohort",
        target_population=PopulationSpec(description="none"),
        variables_required=[],
    )
    registry = default_analysis_method_registry(cache)
    agent = AnalyticsAgent(registry)

    result = await agent.run(dataset, plan)
    assert result.methods_run == []
    assert result.data_quality_notes
