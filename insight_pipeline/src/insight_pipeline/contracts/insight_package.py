"""The Executive Report Package — see docs/PLATFORM_ARCHITECTURE.md §15.
The single object the frontend ever consumes. Everything needed to render a
full report lives inside it; nothing downstream of this contract calls
analytics, plotting, or an LLM."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from hypothesis_agent.contracts.hypothesis import HypothesisPackage
from hypothesis_agent.contracts.memory import ReasoningTraceEntry
from insight_pipeline.contracts.analytics import AnalyticsResult
from insight_pipeline.contracts.business_insight import BusinessInsights
from insight_pipeline.contracts.grounding import GroundingMap
from insight_pipeline.contracts.investigation import InvestigationPlan
from insight_pipeline.contracts.narrative import Narrative
from insight_pipeline.contracts.root_cause import RootCauseGraph
from insight_pipeline.contracts.visualization import GeneratedFigure, VisualizationPlan


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class InsightPackage(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("insight"))
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    hypothesis_package: HypothesisPackage
    # Optional so legacy reports generated before the V2 grounding stage (which
    # have no grounding_map) still deserialize and load. The pipeline always
    # populates it for new insights; the frontend treats absent as "no grounding
    # map" (see insight.html).
    grounding_map: GroundingMap | None = None
    investigation_plan: InvestigationPlan
    analytics_results: AnalyticsResult
    root_cause_graph: RootCauseGraph
    business_insights: BusinessInsights
    narrative: Narrative
    visualization_plan: VisualizationPlan
    generated_figures: list[GeneratedFigure] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    trace: list[ReasoningTraceEntry] = Field(default_factory=list)
