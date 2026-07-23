"""Root Cause Discovery Agent — see docs/PLATFORM_ARCHITECTURE.md §10. Not
"summarize the statistics" — mechanism discovery."""

from __future__ import annotations

from insight_pipeline.contracts.analytics import AnalyticsResult
from insight_pipeline.contracts.investigation import InvestigationPlan
from insight_pipeline.contracts.root_cause import RootCauseGraph
from insight_pipeline.logging_setup import get_logger
from insight_pipeline.plugins.root_cause_strategies.base import RootCauseStrategyPlugin
from insight_pipeline.ports.organization_knowledge_retriever import (
    OrganizationKnowledgeRetriever,
)

logger = get_logger("agents.root_cause")


class RootCauseDiscoveryAgent:
    def __init__(
        self, strategy: RootCauseStrategyPlugin, knowledge_retriever: OrganizationKnowledgeRetriever
    ) -> None:
        self._strategy = strategy
        self._knowledge_retriever = knowledge_retriever

    async def run(
        self, plan: InvestigationPlan, analytics: AnalyticsResult
    ) -> RootCauseGraph:
        query = " ".join(plan.statistical_questions) or " ".join(plan.business_questions)
        knowledge = await self._knowledge_retriever.retrieve(query, plan.organization_id, top_k=5) if query else []
        graph = await self._strategy.discover(plan, analytics, knowledge)
        logger.info(
            "root cause graph produced",
            extra={"extra_fields": {"nodes": len(graph.nodes), "edges": len(graph.edges)}},
        )
        return graph
