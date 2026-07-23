from __future__ import annotations

from typing import TypedDict

from hypothesis_agent.contracts.hypothesis import HypothesisPackage
from hypothesis_agent.contracts.memory import ReasoningTraceEntry
from insight_pipeline.contracts.analytics import AnalyticsResult
from insight_pipeline.contracts.business_insight import BusinessInsights
from insight_pipeline.contracts.dataset import RetrievedDataset
from insight_pipeline.contracts.grounding import GroundingMap
from insight_pipeline.contracts.investigation import InvestigationPlan
from insight_pipeline.contracts.narrative import Narrative
from insight_pipeline.contracts.root_cause import RootCauseGraph
from insight_pipeline.contracts.visualization import GeneratedFigure, VisualizationPlan


class PipelineState(TypedDict, total=False):
    hypothesis_package: HypothesisPackage
    grounding_map: GroundingMap
    investigation_plan: InvestigationPlan
    retrieved_dataset: RetrievedDataset
    analytics_result: AnalyticsResult
    root_cause_graph: RootCauseGraph
    business_insights: BusinessInsights
    narrative: Narrative
    visualization_plan: VisualizationPlan
    generated_figures: list[GeneratedFigure]
    trace: list[ReasoningTraceEntry]
