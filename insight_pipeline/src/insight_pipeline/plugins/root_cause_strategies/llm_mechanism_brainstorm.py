from __future__ import annotations

from pydantic import BaseModel, Field

from hypothesis_agent.contracts.llm import LLMMessage, LLMRequest
from hypothesis_agent.ports.llm_service import LLMService
from insight_pipeline.contracts.analytics import AnalyticsResult
from insight_pipeline.contracts.investigation import InvestigationPlan
from insight_pipeline.contracts.organization_knowledge import OrganizationKnowledge
from insight_pipeline.contracts.root_cause import CausalEdge, CausalNode, RootCauseGraph
from insight_pipeline.plugins.root_cause_strategies.base import RootCauseStrategyPlugin
from insight_pipeline.prompts.registry import PromptRegistry


class RootCauseResponse(BaseModel):
    nodes: list[CausalNode] = Field(default_factory=list)
    edges: list[CausalEdge] = Field(default_factory=list)
    potential_mechanisms: list[str] = Field(default_factory=list)
    supporting_evidence: list[str] = Field(default_factory=list)
    alternative_explanations: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)


def render_analytics(analytics: AnalyticsResult) -> str:
    if not analytics.methods_run:
        return "(no analysis methods produced results)"
    return "\n".join(
        f"- {r.method} on {r.variables_involved}: statistic={r.statistic}, p={r.p_value} — {r.interpretation_notes}"
        for r in analytics.methods_run
    )


class LLMMechanismBrainstormPlugin(RootCauseStrategyPlugin):
    """Default root-cause strategy: one structured LLM call proposing a
    causal graph. A future StatisticalCausalDiscoveryPlugin (e.g. a
    PC-algorithm-style structure-learning method) can register alongside
    this with zero change to the Root Cause Agent."""

    strategy_name = "llm_mechanism_brainstorm"

    def __init__(self, llm_service: LLMService, prompts: PromptRegistry) -> None:
        self._llm = llm_service
        self._prompts = prompts

    async def discover(
        self,
        plan: InvestigationPlan,
        analytics: AnalyticsResult,
        knowledge: list[OrganizationKnowledge],
    ) -> RootCauseGraph:
        template = self._prompts.get("root_cause")
        knowledge_text = (
            "\n".join(f"- [{k.category}] {k.title}: {k.excerpt}" for k in knowledge)
            or "(none available)"
        )
        rendered = template.render(
            statistical_questions="; ".join(plan.statistical_questions) or "(none specified)",
            analytics_summary=render_analytics(analytics),
            knowledge=knowledge_text,
        )
        request = LLMRequest(
            messages=[
                LLMMessage(role="system", content=rendered.system),
                LLMMessage(role="user", content=rendered.user),
            ],
            temperature=0.6,
        )
        result = await self._llm.complete_structured(request, RootCauseResponse)
        return RootCauseGraph(
            nodes=result.nodes,
            edges=result.edges,
            potential_mechanisms=result.potential_mechanisms,
            supporting_evidence=result.supporting_evidence,
            alternative_explanations=result.alternative_explanations,
            confidence=result.confidence,
        )
