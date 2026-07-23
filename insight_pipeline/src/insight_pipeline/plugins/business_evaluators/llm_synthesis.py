from __future__ import annotations

from pydantic import BaseModel, Field

from hypothesis_agent.contracts.llm import LLMMessage, LLMRequest
from hypothesis_agent.ports.llm_service import LLMService
from insight_pipeline.contracts.business_insight import (
    BusinessFinding,
    BusinessOpportunity,
    BusinessRisk,
    Recommendation,
)
from insight_pipeline.plugins.business_evaluators.base import (
    BusinessEvaluatorContext,
    BusinessEvaluatorPlugin,
)
from insight_pipeline.prompts.registry import PromptRegistry


class BusinessSynthesisResponse(BaseModel):
    findings: list[BusinessFinding] = Field(default_factory=list)
    risks: list[BusinessRisk] = Field(default_factory=list)
    opportunities: list[BusinessOpportunity] = Field(default_factory=list)
    financial_impact: str | None = None
    organizational_impact: str = ""
    employee_impact: str = ""
    strategic_recommendations: list[Recommendation] = Field(default_factory=list)
    priority_ranking: list[str] = Field(default_factory=list)


class LLMBusinessSynthesisEvaluator(BusinessEvaluatorPlugin):
    """Default (and, for now, only) business lens: one structured LLM call
    covering findings/risks/opportunities/impact/recommendations together.
    Specialized lenses (a dedicated FinancialImpactEvaluator, RiskEvaluator,
    ROIEstimator, ...) are natural future plugins registered alongside this
    one with zero change to the Business Insight Agent — see
    docs/PLATFORM_ARCHITECTURE.md §11/§23 ("grow ... as plugins")."""

    lens_name = "llm_synthesis"

    def __init__(self, llm_service: LLMService, prompts: PromptRegistry) -> None:
        self._llm = llm_service
        self._prompts = prompts

    async def evaluate(self, context: BusinessEvaluatorContext) -> dict:
        template = self._prompts.get("business_insight")
        knowledge_text = (
            "\n".join(f"- [{k.category}] {k.title}: {k.excerpt}" for k in context.knowledge)
            or "(none available)"
        )
        rendered = template.render(
            mechanisms="\n".join(f"- {m}" for m in context.root_cause.potential_mechanisms) or "(none)",
            evidence="\n".join(f"- {e}" for e in context.root_cause.supporting_evidence) or "(none)",
            alternatives="\n".join(f"- {a}" for a in context.root_cause.alternative_explanations)
            or "(none)",
            knowledge=knowledge_text,
        )
        request = LLMRequest(
            messages=[
                LLMMessage(role="system", content=rendered.system),
                LLMMessage(role="user", content=rendered.user),
            ],
            temperature=0.5,
        )
        result = await self._llm.complete_structured(request, BusinessSynthesisResponse)
        return result.model_dump()
