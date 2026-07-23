"""Visualization Planner (rule-based, deterministic) + Plot Generation Tool
against the real Book1_standardized.xlsx cohort and real analytics results —
real matplotlib rendering, actual PNG files written to disk."""

from pathlib import Path

import pytest

from insight_pipeline.adapters.employee_data.excel_repository import ExcelEmployeeDataRepository
from insight_pipeline.adapters.employee_data.handle_cache import InMemoryDatasetHandleCache
from insight_pipeline.adapters.plotting.matplotlib_engine import MatplotlibPlottingEngine
from insight_pipeline.agents.analytics.facade import AnalyticsAgent
from insight_pipeline.agents.visualization_planner.facade import VisualizationPlannerAgent
from insight_pipeline.contracts.business_insight import BusinessInsights
from insight_pipeline.contracts.dataset import DatasetMetadata, RetrievalQuery, RetrievedDataset
from insight_pipeline.contracts.investigation import InvestigationPlan, PopulationSpec, VariableSpec
from insight_pipeline.plugins.analysis_methods import default_analysis_method_registry
from insight_pipeline.plugins.visualization_recommenders.rule_based import (
    RuleBasedVisualizationRecommender,
)
from insight_pipeline.tools.plot_generation.chart_data_resolver import DefaultChartDataResolver
from insight_pipeline.tools.plot_generation.tool import PlotGenerationTool
from hypothesis_agent.contracts.organization import AttributeField

_XLSX_PATH = Path(__file__).parents[3] / "Book1_standardized.xlsx"

pytestmark = pytest.mark.skipif(not _XLSX_PATH.exists(), reason="Book1_standardized.xlsx not present")


def _field(name: str, category: str, data_type: str) -> AttributeField:
    return AttributeField(name=name, category=category, data_type=data_type, coverage_ratio=1.0)


async def test_visualization_planner_and_plot_tool_end_to_end(tmp_path):
    cache = InMemoryDatasetHandleCache()
    repo = ExcelEmployeeDataRepository(_XLSX_PATH, cache)
    handle = await repo.resolve(
        RetrievalQuery(
            organization_id="shl-sample-cohort",
            requested_fields=["4_personality", "7_personality", "1.1_personality", "MQ.E.1_cat"],
        )
    )
    dataset = RetrievedDataset(
        investigation_plan_id="plan_viz",
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
        id="plan_viz",
        hypothesis_package_id="pkg_viz",
        organization_id="shl-sample-cohort",
        target_population=PopulationSpec(description="all candidates"),
        variables_required=[
            VariableSpec(name="4_personality", role="independent", expected_type="numeric"),
            VariableSpec(name="7_personality", role="dependent", expected_type="numeric"),
            VariableSpec(name="1.1_personality", role="independent", expected_type="categorical"),
            VariableSpec(name="MQ.E.1_cat", role="control", expected_type="categorical"),
        ],
    )
    analytics_agent = AnalyticsAgent(default_analysis_method_registry(cache))
    analytics = await analytics_agent.run(dataset, plan)
    assert analytics.methods_run

    viz_agent = VisualizationPlannerAgent(RuleBasedVisualizationRecommender(), max_figures=6)
    viz_plan = await viz_agent.run(BusinessInsights(), analytics)
    assert viz_plan.specs

    resolver = DefaultChartDataResolver(cache)
    engine = MatplotlibPlottingEngine(tmp_path)
    tool = PlotGenerationTool(resolver, engine)

    figures = []
    for spec in viz_plan.specs:
        figure = await tool.render(spec, handle)
        if figure is not None:
            figures.append(figure)

    assert figures, "expected at least one rendered figure"
    for figure in figures:
        assert Path(figure.file_ref).exists()
        assert Path(figure.file_ref).stat().st_size > 0


async def test_quadrant_divergence_chart_renders_real_360_data(tmp_path):
    from insight_pipeline.contracts.visualization import ChartTheme, VisualizationSpec

    cache = InMemoryDatasetHandleCache()
    repo = ExcelEmployeeDataRepository(_XLSX_PATH, cache)
    handle = await repo.resolve(
        RetrievalQuery(
            organization_id="shl-sample-cohort",
            requested_fields=["360.4_self", "360.4_manager"],
        )
    )

    resolver = DefaultChartDataResolver(cache)
    engine = MatplotlibPlottingEngine(tmp_path)
    tool = PlotGenerationTool(resolver, engine, ChartTheme())

    spec = VisualizationSpec(
        title="Self vs Manager rating — dimension 4 (360)",
        visualization_type="quadrant_divergence",
        variables=["360.4_self", "360.4_manager"],
        data_requirements=["360.4_self", "360.4_manager"],
        executive_message="Where self-perception diverges from manager perception.",
    )
    figure = await tool.render(spec, handle)

    assert figure is not None
    file_path = Path(figure.file_ref)
    assert file_path.exists()
    assert file_path.stat().st_size > 0

    resolved = await resolver.resolve(spec, handle)
    assert resolved.x_threshold is not None
    assert resolved.y_threshold is not None
    assert resolved.raw_points
