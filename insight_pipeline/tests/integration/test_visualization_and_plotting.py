"""Visualization Planner (rule-based, deterministic) + Plot Generation Tool
against the real Book1.xlsx cohort and real analytics results — real
matplotlib rendering, actual PNG files written to disk."""

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

_XLSX_PATH = Path(__file__).parents[3] / "Book1.xlsx"

pytestmark = pytest.mark.skipif(not _XLSX_PATH.exists(), reason="Book1.xlsx not present")


def _field(name: str, category: str, data_type: str) -> AttributeField:
    return AttributeField(name=name, category=category, data_type=data_type, coverage_ratio=1.0)


async def test_visualization_planner_and_plot_tool_end_to_end(tmp_path):
    cache = InMemoryDatasetHandleCache()
    repo = ExcelEmployeeDataRepository(_XLSX_PATH, cache)
    handle = await repo.resolve(
        RetrievalQuery(
            organization_id="shl-sample-cohort",
            requested_fields=["Makes_Quick_Decisions", "Takes_Responsibility", "Decision_Making", "Leadership"],
        )
    )
    dataset = RetrievedDataset(
        investigation_plan_id="plan_viz",
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
        id="plan_viz",
        hypothesis_package_id="pkg_viz",
        organization_id="shl-sample-cohort",
        target_population=PopulationSpec(description="all candidates"),
        variables_required=[
            VariableSpec(name="Makes_Quick_Decisions", role="independent", expected_type="numeric"),
            VariableSpec(name="Takes_Responsibility", role="dependent", expected_type="numeric"),
            VariableSpec(name="Decision_Making", role="independent", expected_type="categorical"),
            VariableSpec(name="Leadership", role="control", expected_type="categorical"),
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
