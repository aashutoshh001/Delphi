from __future__ import annotations

from hypothesis_agent.contracts.llm import LLMMessage, LLMRequest
from hypothesis_agent.ports.llm_service import LLMService
from insight_pipeline.contracts.business_insight import BusinessInsights
from insight_pipeline.contracts.narrative import Narrative
from insight_pipeline.contracts.root_cause import RootCauseGraph
from insight_pipeline.plugins.narrative_strategies.base import NarrativeStrategyPlugin
from insight_pipeline.prompts.registry import PromptRegistry


class BalancedNarrativeStrategy(NarrativeStrategyPlugin):
    """Default narrative framing: gives risks and opportunities equal
    weight. RiskLedNarrativeStrategy / OpportunityLedNarrativeStrategy are
    natural future siblings (docs/PLATFORM_ARCHITECTURE.md §12)."""

    strategy_name = "balanced"

    def __init__(self, llm_service: LLMService, prompts: PromptRegistry) -> None:
        self._llm = llm_service
        self._prompts = prompts

    async def narrate(
        self,
        insights: BusinessInsights,
        root_cause: RootCauseGraph,
        session_id: str | None = None,
    ) -> Narrative:
        template = self._prompts.get("narrative")
        rendered = template.render(
            findings="\n".join(f"- {f.statement}" for f in insights.findings) or "(none)",
            risks="\n".join(f"- [{r.severity}] {r.description}" for r in insights.risks) or "(none)",
            opportunities="\n".join(f"- {o.description}" for o in insights.opportunities) or "(none)",
            recommendations="\n".join(
                f"- (p{r.priority}) {r.action}: {r.rationale}" for r in insights.strategic_recommendations
            )
            or "(none)",
        )
        request = LLMRequest(
            messages=[
                LLMMessage(role="system", content=rendered.system),
                LLMMessage(role="user", content=rendered.user),
            ],
            temperature=0.6,
            metadata={"session_id": session_id} if session_id else {},
        )
        return await self._llm.complete_structured(request, Narrative)
