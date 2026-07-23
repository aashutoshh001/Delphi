from __future__ import annotations

from hypothesis_agent.contracts.llm import LLMMessage, LLMRequest
from hypothesis_agent.ports.llm_service import LLMService
from insight_pipeline.contracts.analytics import AnalyticsResult
from insight_pipeline.contracts.business_insight import BusinessInsights
from insight_pipeline.contracts.visualization import VisualizationPlan
from insight_pipeline.plugins.visualization_recommenders.base import (
    VisualizationRecommenderPlugin,
)
from insight_pipeline.prompts.registry import PromptRegistry


def _available_columns(analytics: AnalyticsResult) -> list[str]:
    columns: list[str] = []
    for result in analytics.methods_run:
        for column in result.variables_involved:
            if column not in columns:
                columns.append(column)
    return columns


class LLMVisualizationRecommender(VisualizationRecommenderPlugin):
    """Default: one structured LLM call proposing however many charts the
    evidence warrants. RuleBasedVisualizationRecommender is the offline/
    no-LLM fallback (docs/PLATFORM_ARCHITECTURE.md §13)."""

    strategy_name = "llm_recommender"

    def __init__(self, llm_service: LLMService, prompts: PromptRegistry) -> None:
        self._llm = llm_service
        self._prompts = prompts

    async def recommend(
        self,
        insights: BusinessInsights,
        analytics: AnalyticsResult,
        session_id: str | None = None,
    ) -> VisualizationPlan:
        columns = _available_columns(analytics)
        template = self._prompts.get("visualization_plan")
        rendered = template.render(
            findings="\n".join(f"- {f.statement}" for f in insights.findings) or "(none)",
            analytics_summary="\n".join(
                f"- {r.method} on {r.variables_involved}: {r.interpretation_notes}"
                for r in analytics.methods_run
            )
            or "(none)",
            available_columns=", ".join(columns) or "(none available)",
        )
        request = LLMRequest(
            messages=[
                LLMMessage(role="system", content=rendered.system),
                LLMMessage(role="user", content=rendered.user),
            ],
            temperature=0.5,
            metadata={"session_id": session_id} if session_id else {},
        )
        plan = await self._llm.complete_structured(request, VisualizationPlan)
        known = set(columns)
        for spec in plan.specs:
            spec.variables = [v for v in spec.variables if v in known] or columns[:2]
            spec.data_requirements = spec.data_requirements or spec.variables
        return plan
