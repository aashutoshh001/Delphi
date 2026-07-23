"""Root Cause Discovery Agent — see docs/PLATFORM_ARCHITECTURE.md §10. Not
"summarize the statistics" — mechanism discovery.

Grounding enforcement (V2 architecture plan Part 4E): every causal edge must
cite evidence that traces back to something the Analytics Agent actually
computed — a method name or a real variable it analyzed. An edge whose
evidence_refs don't mention any of those is dropped here, deterministically,
the same "don't rely on the LLM alone" discipline used everywhere else in
this platform (construct grounding, investigation planning, the hypothesis
agent's dedup guard)."""

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


def _valid_evidence_tokens(analytics: AnalyticsResult) -> set[str]:
    tokens = set()
    for result in analytics.methods_run:
        tokens.add(result.method.lower())
        tokens.update(v.lower() for v in result.variables_involved)
    return tokens


def _edge_is_evidenced(edge, tokens: set[str]) -> bool:
    if not edge.evidence_refs:
        return False
    if not tokens:
        # No analytics ran at all — evidence can't reference anything real,
        # so no edge can be considered grounded.
        return False
    combined = " ".join(edge.evidence_refs).lower()
    return any(token in combined for token in tokens)


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

        tokens = _valid_evidence_tokens(analytics)
        kept_edges = [e for e in graph.edges if _edge_is_evidenced(e, tokens)]
        dropped = len(graph.edges) - len(kept_edges)
        if dropped:
            logger.warning(
                "dropped ungrounded root-cause edge(s) — evidence_refs did not cite any real analytics result",
                extra={"extra_fields": {"dropped": dropped, "kept": len(kept_edges)}},
            )
        graph = graph.model_copy(update={"edges": kept_edges})

        logger.info(
            "root cause graph produced",
            extra={"extra_fields": {"nodes": len(graph.nodes), "edges": len(graph.edges)}},
        )
        return graph
