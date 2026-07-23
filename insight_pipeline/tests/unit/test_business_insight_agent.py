from hypothesis_agent.adapters.embeddings.hash_embedding_service import HashEmbeddingService
from hypothesis_agent.adapters.llm.mock_llm_service import MockLLMService
from insight_pipeline.adapters.organization_knowledge.embedding_retriever import (
    EmbeddingOrganizationKnowledgeRetriever,
)
from insight_pipeline.adapters.organization_knowledge.in_memory_repository import (
    InMemoryOrganizationKnowledgeRepository,
)
from insight_pipeline.agents.business_insight.facade import BusinessInsightAgent
from insight_pipeline.contracts.analytics import AnalyticsResult
from insight_pipeline.contracts.investigation import InvestigationPlan, PopulationSpec
from insight_pipeline.contracts.root_cause import RootCauseGraph
from insight_pipeline.plugins.business_evaluators.llm_synthesis import LLMBusinessSynthesisEvaluator
from insight_pipeline.prompts.registry import default_prompt_registry


async def test_business_insight_agent_merges_single_evaluator():
    llm = MockLLMService()
    evaluator = LLMBusinessSynthesisEvaluator(llm, default_prompt_registry())
    retriever = EmbeddingOrganizationKnowledgeRetriever(
        InMemoryOrganizationKnowledgeRepository(), HashEmbeddingService()
    )
    agent = BusinessInsightAgent([evaluator], retriever)

    plan = InvestigationPlan(
        hypothesis_package_id="pkg_1",
        organization_id="org-1",
        target_population=PopulationSpec(description="all"),
    )
    analytics = AnalyticsResult(investigation_plan_id=plan.id, dataset_id="dataset_1")
    root_cause = RootCauseGraph(potential_mechanisms=["overload concentrates in senior ICs"])

    insights = await agent.run(plan, analytics, root_cause)

    assert isinstance(insights.findings, list)
    assert isinstance(insights.risks, list)


def test_business_insight_agent_requires_at_least_one_evaluator():
    import pytest

    from insight_pipeline.adapters.organization_knowledge.embedding_retriever import (
        EmbeddingOrganizationKnowledgeRetriever,
    )
    from insight_pipeline.adapters.organization_knowledge.in_memory_repository import (
        InMemoryOrganizationKnowledgeRepository,
    )

    retriever = EmbeddingOrganizationKnowledgeRetriever(
        InMemoryOrganizationKnowledgeRepository(), HashEmbeddingService()
    )
    with pytest.raises(ValueError):
        BusinessInsightAgent([], retriever)
