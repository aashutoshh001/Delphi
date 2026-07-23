"""Business Insight Agent — see docs/PLATFORM_ARCHITECTURE.md §11. Not
statistical reporting — consulting synthesis."""

from __future__ import annotations

from insight_pipeline.contracts.analytics import AnalyticsResult
from insight_pipeline.contracts.business_insight import (
    BusinessFinding,
    BusinessInsights,
    BusinessOpportunity,
    BusinessRisk,
    Recommendation,
)
from insight_pipeline.contracts.investigation import InvestigationPlan
from insight_pipeline.contracts.root_cause import RootCauseGraph
from insight_pipeline.logging_setup import get_logger
from insight_pipeline.plugins.business_evaluators.base import (
    BusinessEvaluatorContext,
    BusinessEvaluatorPlugin,
)
from insight_pipeline.ports.organization_knowledge_retriever import (
    OrganizationKnowledgeRetriever,
)

logger = get_logger("agents.business_insight")


def _merge(partials: list[dict]) -> BusinessInsights:
    """Merges every registered lens's contribution — concatenates list
    fields, keeps the first non-empty prose field. Trivial with one lens
    today; the merge itself is what stays stable as more lenses register."""
    findings: list[BusinessFinding] = []
    risks: list[BusinessRisk] = []
    opportunities: list[BusinessOpportunity] = []
    recommendations: list[Recommendation] = []
    priority_ranking: list[str] = []
    financial_impact = None
    organizational_impact = ""
    employee_impact = ""

    for partial in partials:
        findings.extend(BusinessFinding.model_validate(f) for f in partial.get("findings", []))
        risks.extend(BusinessRisk.model_validate(r) for r in partial.get("risks", []))
        opportunities.extend(
            BusinessOpportunity.model_validate(o) for o in partial.get("opportunities", [])
        )
        recommendations.extend(
            Recommendation.model_validate(r) for r in partial.get("strategic_recommendations", [])
        )
        priority_ranking.extend(p for p in partial.get("priority_ranking", []) if p not in priority_ranking)
        financial_impact = financial_impact or partial.get("financial_impact")
        organizational_impact = organizational_impact or partial.get("organizational_impact", "")
        employee_impact = employee_impact or partial.get("employee_impact", "")

    return BusinessInsights(
        findings=findings,
        risks=risks,
        opportunities=opportunities,
        financial_impact=financial_impact,
        organizational_impact=organizational_impact,
        employee_impact=employee_impact,
        strategic_recommendations=recommendations,
        priority_ranking=priority_ranking,
    )


class BusinessInsightAgent:
    def __init__(
        self, evaluators: list[BusinessEvaluatorPlugin], knowledge_retriever: OrganizationKnowledgeRetriever
    ) -> None:
        if not evaluators:
            raise ValueError("BusinessInsightAgent requires at least one BusinessEvaluatorPlugin")
        self._evaluators = evaluators
        self._knowledge_retriever = knowledge_retriever

    async def run(
        self,
        plan: InvestigationPlan,
        analytics: AnalyticsResult,
        root_cause: RootCauseGraph,
    ) -> BusinessInsights:
        query = " ".join(root_cause.potential_mechanisms) or " ".join(plan.business_questions)
        knowledge = (
            await self._knowledge_retriever.retrieve(query, plan.organization_id, top_k=5)
            if query
            else []
        )
        context = BusinessEvaluatorContext(analytics=analytics, root_cause=root_cause, knowledge=knowledge)
        partials = [await evaluator.evaluate(context) for evaluator in self._evaluators]
        insights = _merge(partials)
        logger.info(
            "business insights produced",
            extra={
                "extra_fields": {
                    "findings": len(insights.findings),
                    "risks": len(insights.risks),
                    "opportunities": len(insights.opportunities),
                }
            },
        )
        return insights
