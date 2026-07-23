"""Visualization Planner Agent — see docs/PLATFORM_ARCHITECTURE.md §13.
Decides WHAT to chart, never draws anything itself."""

from __future__ import annotations

from insight_pipeline.contracts.analytics import AnalyticsResult
from insight_pipeline.contracts.business_insight import BusinessInsights
from insight_pipeline.contracts.visualization import VisualizationPlan
from insight_pipeline.logging_setup import get_logger
from insight_pipeline.plugins.visualization_recommenders.base import (
    VisualizationRecommenderPlugin,
)

logger = get_logger("agents.visualization_planner")


class VisualizationPlannerAgent:
    def __init__(self, recommender: VisualizationRecommenderPlugin, max_figures: int = 6) -> None:
        self._recommender = recommender
        self._max_figures = max_figures

    async def run(self, insights: BusinessInsights, analytics: AnalyticsResult) -> VisualizationPlan:
        plan = await self._recommender.recommend(insights, analytics)
        specs = sorted(plan.specs, key=lambda s: s.priority)[: self._max_figures]
        logger.info(
            "visualization plan produced",
            extra={"extra_fields": {"chart_count": len(specs)}},
        )
        return VisualizationPlan(id=plan.id, specs=specs)
