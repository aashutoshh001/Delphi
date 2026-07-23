"""Analytics Agent against the real Book1.xlsx cohort — real scipy
statistics, not mocked, so this validates the whole plugin selection +
concurrent execution path against real data shapes (numeric granular
indicators, categorical competency buckets)."""

from pathlib import Path

import pytest

from insight_pipeline.adapters.employee_data.excel_repository import ExcelEmployeeDataRepository
from insight_pipeline.adapters.employee_data.handle_cache import InMemoryDatasetHandleCache
from insight_pipeline.agents.analytics.facade import AnalyticsAgent
from insight_pipeline.contracts.dataset import DatasetMetadata, RetrievalQuery, RetrievedDataset
from insight_pipeline.contracts.investigation import InvestigationPlan, PopulationSpec, VariableSpec
from insight_pipeline.plugins.analysis_methods import default_analysis_method_registry
from hypothesis_agent.contracts.organization import AttributeField

_XLSX_PATH = Path(__file__).parents[3] / "Book1.xlsx"

pytestmark = pytest.mark.skipif(not _XLSX_PATH.exists(), reason="Book1.xlsx not present")


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
        ["Makes_Quick_Decisions", "Takes_Responsibility", "Decision_Making", "Leadership"],
    )
    dataset = RetrievedDataset(
        investigation_plan_id="plan_test",
        handle=handle,
        metadata=DatasetMetadata(
            fields=[
                _field("Makes_Quick_Decisions", "behavioural_competency", "ordinal"),
                _field("Takes_Responsibility", "behavioural_competency", "ordinal"),
                _field("Decision_Making", "behavioural_competency", "categorical"),
                _field("Leadership", "behavioural_competency", "categorical"),
            ]
        ),
    )
    plan = InvestigationPlan(
        id="plan_test",
        hypothesis_package_id="pkg_test",
        organization_id="shl-sample-cohort",
        target_population=PopulationSpec(description="all candidates"),
        variables_required=[
            VariableSpec(name="Makes_Quick_Decisions", role="independent", expected_type="numeric"),
            VariableSpec(name="Takes_Responsibility", role="dependent", expected_type="numeric"),
            VariableSpec(name="Decision_Making", role="independent", expected_type="categorical"),
            VariableSpec(name="Leadership", role="control", expected_type="categorical"),
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
    for r in result.methods_run:
        assert r.p_value is not None, f"{r.method} produced no p_value"
        print(r.method, r.interpretation_notes)


async def test_analytics_agent_handles_no_applicable_methods_gracefully():
    cache = InMemoryDatasetHandleCache()
    handle = await _retrieve(cache, ["Candidate_ID"])
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
