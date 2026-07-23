"""Top-level orchestrator — see docs/PLATFORM_ARCHITECTURE.md §16. The
downstream analog of hypothesis_agent's own search-loop graph: each node
invokes exactly one agent's facade and hands its typed output to the next.
No analysis logic lives here, only wiring."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from hypothesis_agent.contracts.memory import ReasoningTraceEntry
from langgraph.graph import END, START, StateGraph

from insight_pipeline.agents.analytics.facade import AnalyticsAgent
from insight_pipeline.agents.business_insight.facade import BusinessInsightAgent
from insight_pipeline.agents.data_retrieval.facade import DataRetrievalAgent
from insight_pipeline.agents.investigation_planner.facade import InvestigationPlannerAgent
from insight_pipeline.agents.narrative.facade import NarrativeAgent
from insight_pipeline.agents.root_cause.facade import RootCauseDiscoveryAgent
from insight_pipeline.agents.visualization_planner.facade import VisualizationPlannerAgent
from insight_pipeline.contracts.visualization import ChartTheme
from insight_pipeline.di.container import PipelineDependencies
from insight_pipeline.logging_setup import get_logger
from insight_pipeline.orchestrator.state import PipelineState
from insight_pipeline.tools.plot_generation.chart_data_resolver import DefaultChartDataResolver
from insight_pipeline.tools.plot_generation.tool import PlotGenerationTool

logger = get_logger("orchestrator")


def _trace(state: PipelineState, step: str, summary: str) -> list[ReasoningTraceEntry]:
    return state.get("trace", []) + [
        ReasoningTraceEntry(step=step, iteration=0, summary=summary, timestamp=datetime.now(timezone.utc))
    ]


def build_pipeline_graph(deps: PipelineDependencies):
    investigation_planner = InvestigationPlannerAgent(
        deps.investigation_planner_engine, deps.knowledge_retriever
    )
    data_retrieval = DataRetrievalAgent(deps.dataset_retriever)
    analytics = AnalyticsAgent(
        deps.analysis_method_registry, deps.config.analytics.max_methods_per_investigation
    )
    root_cause = RootCauseDiscoveryAgent(deps.root_cause_strategy, deps.knowledge_retriever)
    business_insight = BusinessInsightAgent(deps.business_evaluators, deps.knowledge_retriever)
    narrative = NarrativeAgent(deps.narrative_strategy)
    visualization_planner = VisualizationPlannerAgent(
        deps.visualization_recommender, deps.config.visualization.max_figures_per_report
    )
    plot_tool = PlotGenerationTool(
        DefaultChartDataResolver(deps.handle_cache), deps.plotting_engine, ChartTheme()
    )

    async def investigation_planner_node(state: PipelineState) -> dict[str, Any]:
        plan = await investigation_planner.run(state["hypothesis_package"])
        return {
            "investigation_plan": plan,
            "trace": _trace(state, "investigation_planner", f"{len(plan.variables_required)} variables planned"),
        }

    async def data_retrieval_node(state: PipelineState) -> dict[str, Any]:
        dataset = await data_retrieval.run(state["investigation_plan"])
        return {
            "retrieved_dataset": dataset,
            "trace": _trace(state, "data_retrieval", f"{dataset.handle.row_count} rows retrieved"),
        }

    async def analytics_node(state: PipelineState) -> dict[str, Any]:
        result = await analytics.run(state["retrieved_dataset"], state["investigation_plan"])
        return {
            "analytics_result": result,
            "trace": _trace(state, "analytics", f"{len(result.methods_run)} method(s) run"),
        }

    async def root_cause_node(state: PipelineState) -> dict[str, Any]:
        graph = await root_cause.run(state["investigation_plan"], state["analytics_result"])
        return {
            "root_cause_graph": graph,
            "trace": _trace(state, "root_cause", f"{len(graph.nodes)} node(s), {len(graph.edges)} edge(s)"),
        }

    async def business_insight_node(state: PipelineState) -> dict[str, Any]:
        insights = await business_insight.run(
            state["investigation_plan"], state["analytics_result"], state["root_cause_graph"]
        )
        return {
            "business_insights": insights,
            "trace": _trace(state, "business_insight", f"{len(insights.findings)} finding(s)"),
        }

    async def narrative_node(state: PipelineState) -> dict[str, Any]:
        result = await narrative.run(state["business_insights"], state["root_cause_graph"])
        return {"narrative": result, "trace": _trace(state, "narrative", result.executive_summary[:120])}

    async def visualization_planner_node(state: PipelineState) -> dict[str, Any]:
        plan = await visualization_planner.run(state["business_insights"], state["analytics_result"])
        return {
            "visualization_plan": plan,
            "trace": _trace(state, "visualization_planner", f"{len(plan.specs)} chart(s) planned"),
        }

    async def plot_generation_node(state: PipelineState) -> dict[str, Any]:
        handle = state["retrieved_dataset"].handle
        figures = []
        for spec in state["visualization_plan"].specs:
            figure = await plot_tool.render(spec, handle)
            if figure is not None:
                figures.append(figure)
        return {
            "generated_figures": figures,
            "trace": _trace(state, "plot_generation", f"{len(figures)} figure(s) rendered"),
        }

    builder = StateGraph(PipelineState)
    builder.add_node("investigation_planner", investigation_planner_node)
    builder.add_node("data_retrieval", data_retrieval_node)
    builder.add_node("analytics", analytics_node)
    builder.add_node("root_cause", root_cause_node)
    builder.add_node("business_insight", business_insight_node)
    builder.add_node("narrative", narrative_node)
    builder.add_node("visualization_planner", visualization_planner_node)
    builder.add_node("plot_generation", plot_generation_node)

    builder.add_edge(START, "investigation_planner")
    builder.add_edge("investigation_planner", "data_retrieval")
    builder.add_edge("data_retrieval", "analytics")
    builder.add_edge("analytics", "root_cause")
    builder.add_edge("root_cause", "business_insight")
    builder.add_edge("business_insight", "narrative")
    builder.add_edge("narrative", "visualization_planner")
    builder.add_edge("visualization_planner", "plot_generation")
    builder.add_edge("plot_generation", END)

    return builder.compile()
