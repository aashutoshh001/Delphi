"""New multi-angle analysis methods (V2 architecture plan Part 4D) against
the real Book1_standardized.xlsx cohort — descriptive_stats,
quadrant_divergence, and rater_gap_360, each with real scipy/pandas
computation over real columns."""

from pathlib import Path

import pytest

from hypothesis_agent.contracts.organization import AttributeField
from insight_pipeline.adapters.employee_data.excel_repository import ExcelEmployeeDataRepository
from insight_pipeline.adapters.employee_data.handle_cache import InMemoryDatasetHandleCache
from insight_pipeline.contracts.dataset import DatasetMetadata, RetrievalQuery, RetrievedDataset
from insight_pipeline.contracts.investigation import InvestigationPlan, PopulationSpec, VariableSpec
from insight_pipeline.plugins.analysis_methods.descriptive_stats import DescriptiveStatsPlugin
from insight_pipeline.plugins.analysis_methods.quadrant_divergence import QuadrantDivergencePlugin
from insight_pipeline.plugins.analysis_methods.rater_gap import RaterGapPlugin

_XLSX_PATH = Path(__file__).parents[3] / "Book1_standardized.xlsx"
pytestmark = pytest.mark.skipif(not _XLSX_PATH.exists(), reason="Book1_standardized.xlsx not present")


def _field(name: str, category: str, data_type: str) -> AttributeField:
    return AttributeField(name=name, category=category, data_type=data_type, coverage_ratio=1.0)


async def _retrieve(cache, requested_fields):
    repo = ExcelEmployeeDataRepository(_XLSX_PATH, cache)
    return await repo.resolve(RetrievalQuery(organization_id="shl-sample-cohort", requested_fields=requested_fields))


async def test_descriptive_stats_real_data():
    cache = InMemoryDatasetHandleCache()
    handle = await _retrieve(cache, ["4_personality", "MQ.E.1_cat"])
    plan = InvestigationPlan(
        hypothesis_package_id="pkg_test",
        organization_id="shl-sample-cohort",
        target_population=PopulationSpec(description="all"),
        variables_required=[
            VariableSpec(name="4_personality", role="independent", expected_type="numeric"),
            VariableSpec(name="MQ.E.1_cat", role="control", expected_type="categorical"),
        ],
    )
    plugin = DescriptiveStatsPlugin(cache)
    assert await plugin.is_applicable(plan, DatasetMetadata(fields=[]))
    result = await plugin.run(handle, plan)
    assert result.method == "descriptive_stats"
    assert "4_personality" in result.interpretation_notes
    assert "mean=" in result.interpretation_notes


async def test_quadrant_divergence_real_360_pair():
    cache = InMemoryDatasetHandleCache()
    handle = await _retrieve(cache, ["360.2_self", "360.2_manager"])
    plan = InvestigationPlan(
        hypothesis_package_id="pkg_test",
        organization_id="shl-sample-cohort",
        target_population=PopulationSpec(description="all"),
        variables_required=[
            VariableSpec(name="360.2_self", role="independent", expected_type="numeric"),
            VariableSpec(name="360.2_manager", role="dependent", expected_type="numeric"),
        ],
    )
    plugin = QuadrantDivergencePlugin(cache)
    assert await plugin.is_applicable(
        plan, DatasetMetadata(fields=[_field("360.2_self", "rater_360", "numeric"), _field("360.2_manager", "rater_360", "numeric")])
    )
    result = await plugin.run(handle, plan)
    assert result.method == "quadrant_divergence"
    assert set(result.variables_involved) == {"360.2_self", "360.2_manager"}
    assert result.statistic is not None  # off_diagonal_ratio
    assert "quadrant" in result.interpretation_notes.lower()


async def test_rater_gap_360_real_data():
    cache = InMemoryDatasetHandleCache()
    handle = await _retrieve(cache, ["360.4_self", "360.4_manager", "360.4_report"])
    plan = InvestigationPlan(
        hypothesis_package_id="pkg_test",
        organization_id="shl-sample-cohort",
        target_population=PopulationSpec(description="all"),
        variables_required=[
            VariableSpec(name="360.4_self", role="independent", expected_type="numeric"),
            VariableSpec(name="360.4_manager", role="independent", expected_type="numeric"),
            VariableSpec(name="360.4_report", role="independent", expected_type="numeric"),
        ],
    )
    plugin = RaterGapPlugin(cache)
    metadata = DatasetMetadata(
        fields=[
            _field("360.4_self", "rater_360", "numeric"),
            _field("360.4_manager", "rater_360", "numeric"),
            _field("360.4_report", "rater_360", "numeric"),
        ]
    )
    assert await plugin.is_applicable(plan, metadata)
    result = await plugin.run(handle, plan)
    assert result.method == "rater_gap_360"
    assert "360.4_self" in result.variables_involved
    assert "self" in result.interpretation_notes
    assert "spread" in result.interpretation_notes  # 3 raters present -> consensus spread reported


async def test_rater_gap_not_applicable_without_two_raters():
    cache = InMemoryDatasetHandleCache()
    plan = InvestigationPlan(
        hypothesis_package_id="pkg_test",
        organization_id="shl-sample-cohort",
        target_population=PopulationSpec(description="all"),
        variables_required=[VariableSpec(name="360.1_self", role="independent", expected_type="numeric")],
    )
    plugin = RaterGapPlugin(cache)
    metadata = DatasetMetadata(fields=[_field("360.1_self", "rater_360", "numeric")])
    assert await plugin.is_applicable(plan, metadata) is False
