from hypothesis_agent.adapters.embeddings.hash_embedding_service import HashEmbeddingService
from hypothesis_agent.adapters.llm.mock_llm_service import MockLLMService
from insight_pipeline.adapters.organization_knowledge.embedding_retriever import (
    EmbeddingOrganizationKnowledgeRetriever,
)
from insight_pipeline.adapters.organization_knowledge.in_memory_repository import (
    InMemoryOrganizationKnowledgeRepository,
)
from insight_pipeline.agents.root_cause.facade import RootCauseDiscoveryAgent
from insight_pipeline.contracts.analytics import AnalyticsResult
from insight_pipeline.contracts.investigation import InvestigationPlan, PopulationSpec
from insight_pipeline.plugins.root_cause_strategies.llm_mechanism_brainstorm import (
    LLMMechanismBrainstormPlugin,
)
from insight_pipeline.prompts.registry import default_prompt_registry


async def test_root_cause_agent_produces_a_graph():
    llm = MockLLMService()
    strategy = LLMMechanismBrainstormPlugin(llm, default_prompt_registry())
    retriever = EmbeddingOrganizationKnowledgeRetriever(
        InMemoryOrganizationKnowledgeRepository(), HashEmbeddingService()
    )
    agent = RootCauseDiscoveryAgent(strategy, retriever)

    plan = InvestigationPlan(
        hypothesis_package_id="pkg_1",
        organization_id="org-1",
        target_population=PopulationSpec(description="all"),
        statistical_questions=["does burnout correlate with performance?"],
    )
    analytics = AnalyticsResult(investigation_plan_id=plan.id, dataset_id="dataset_1")

    graph = await agent.run(plan, analytics)

    assert 0.0 <= graph.confidence <= 1.0
    assert isinstance(graph.nodes, list)
    assert isinstance(graph.edges, list)
