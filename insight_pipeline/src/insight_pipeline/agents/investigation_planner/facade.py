"""Investigation Planner Agent — see docs/PLATFORM_ARCHITECTURE.md §7.
Never touches data. Its only question: "what would be needed to validate
this hypothesis?"."""

from __future__ import annotations

from hypothesis_agent.contracts.hypothesis import HypothesisPackage
from insight_pipeline.contracts.investigation import InvestigationPlan
from insight_pipeline.logging_setup import get_logger
from insight_pipeline.ports.investigation_planner_engine import InvestigationPlannerEngine
from insight_pipeline.ports.organization_knowledge_retriever import (
    OrganizationKnowledgeRetriever,
)

logger = get_logger("agents.investigation_planner")


class InvestigationPlannerAgent:
    def __init__(
        self, engine: InvestigationPlannerEngine, knowledge_retriever: OrganizationKnowledgeRetriever
    ) -> None:
        self._engine = engine
        self._knowledge_retriever = knowledge_retriever

    async def run(self, hypothesis_package: HypothesisPackage) -> InvestigationPlan:
        query = f"{hypothesis_package.hypothesis_statement} {hypothesis_package.mechanism_explanation}"
        relevant_knowledge = await self._knowledge_retriever.retrieve(
            query, hypothesis_package.organization_id, top_k=5
        )
        plan = await self._engine.plan(hypothesis_package, relevant_knowledge)
        logger.info(
            "investigation plan produced",
            extra={
                "extra_fields": {
                    "hypothesis_package_id": hypothesis_package.package_id,
                    "variables": len(plan.variables_required),
                }
            },
        )
        return plan
