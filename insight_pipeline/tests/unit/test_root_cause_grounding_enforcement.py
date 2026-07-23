"""Root Cause / Business Insight grounding enforcement (V2 architecture plan
Part 4E) — bypasses the LLM to test the deterministic filtering directly:
an edge/finding with no real evidence must never survive, regardless of
what the underlying strategy/evaluator returned."""

from insight_pipeline.agents.business_insight.facade import BusinessInsightAgent
from insight_pipeline.agents.root_cause.facade import RootCauseDiscoveryAgent
from insight_pipeline.contracts.analytics import AnalysisMethodResult, AnalyticsResult
from insight_pipeline.contracts.business_insight import BusinessFinding
from insight_pipeline.contracts.investigation import InvestigationPlan, PopulationSpec
from insight_pipeline.contracts.root_cause import CausalEdge, CausalNode, RootCauseGraph
from hypothesis_agent.adapters.embeddings.hash_embedding_service import HashEmbeddingService
from insight_pipeline.adapters.organization_knowledge.embedding_retriever import (
    EmbeddingOrganizationKnowledgeRetriever,
)
from insight_pipeline.adapters.organization_knowledge.in_memory_repository import (
    InMemoryOrganizationKnowledgeRepository,
)


def _plan() -> InvestigationPlan:
    return InvestigationPlan(
        hypothesis_package_id="pkg_1",
        organization_id="org-1",
        target_population=PopulationSpec(description="all"),
    )


def _analytics() -> AnalyticsResult:
    return AnalyticsResult(
        investigation_plan_id="plan_1",
        dataset_id="dataset_1",
        methods_run=[
            AnalysisMethodResult(
                method="correlation",
                variables_involved=["4_personality", "tenure_years"],
                statistic=0.4,
                p_value=0.01,
                interpretation_notes="real finding",
            )
        ],
    )


class _StubRootCauseStrategy:
    async def discover(self, plan, analytics, knowledge) -> RootCauseGraph:
        return RootCauseGraph(
            nodes=[CausalNode(id="a", name="A", node_type="driver"), CausalNode(id="b", name="B", node_type="outcome")],
            edges=[
                CausalEdge(
                    source="a", target="b", relationship_type="causes",
                    evidence_refs=["comp_opacity survey result"],  # not real -> dropped
                ),
                CausalEdge(
                    source="a", target="b", relationship_type="correlates_with",
                    evidence_refs=["correlation between 4_personality and tenure_years"],  # real -> kept
                ),
                CausalEdge(
                    source="a", target="b", relationship_type="causes",
                    evidence_refs=[],  # empty -> dropped
                ),
            ],
        )


async def test_root_cause_agent_drops_ungrounded_edges():
    retriever = EmbeddingOrganizationKnowledgeRetriever(
        InMemoryOrganizationKnowledgeRepository(), HashEmbeddingService()
    )
    agent = RootCauseDiscoveryAgent(_StubRootCauseStrategy(), retriever)

    graph = await agent.run(_plan(), _analytics())

    assert len(graph.edges) == 1
    assert "4_personality" in graph.edges[0].evidence_refs[0]


async def test_root_cause_agent_drops_everything_when_analytics_empty():
    retriever = EmbeddingOrganizationKnowledgeRetriever(
        InMemoryOrganizationKnowledgeRepository(), HashEmbeddingService()
    )
    agent = RootCauseDiscoveryAgent(_StubRootCauseStrategy(), retriever)
    empty_analytics = AnalyticsResult(investigation_plan_id="plan_1", dataset_id="dataset_1", methods_run=[])

    graph = await agent.run(_plan(), empty_analytics)

    assert graph.edges == []


class _StubBusinessEvaluator:
    lens_name = "stub"

    async def evaluate(self, context) -> dict:
        return {
            "findings": [
                BusinessFinding(statement="grounded finding", evidence_refs=["correlation"], confidence=0.8).model_dump(),
                BusinessFinding(statement="unsupported finding", evidence_refs=[], confidence=0.5).model_dump(),
            ],
        }


async def test_business_insight_agent_drops_unevidenced_findings():
    retriever = EmbeddingOrganizationKnowledgeRetriever(
        InMemoryOrganizationKnowledgeRepository(), HashEmbeddingService()
    )
    from insight_pipeline.contracts.root_cause import RootCauseGraph as RCG

    agent = BusinessInsightAgent([_StubBusinessEvaluator()], retriever)
    insights = await agent.run(_plan(), _analytics(), RCG())

    assert len(insights.findings) == 1
    assert insights.findings[0].statement == "grounded finding"
