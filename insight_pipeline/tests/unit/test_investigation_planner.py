from hypothesis_agent.adapters.embeddings.hash_embedding_service import HashEmbeddingService
from hypothesis_agent.adapters.llm.mock_llm_service import MockLLMService
from hypothesis_agent.contracts.hypothesis import (
    CritiqueResult,
    EvaluationScorecard,
    HypothesisPackage,
    SearchStatistics,
)
from insight_pipeline.adapters.investigation_planner.direct_llm_engine import (
    DirectLLMInvestigationPlanner,
)
from insight_pipeline.adapters.organization_knowledge.embedding_retriever import (
    EmbeddingOrganizationKnowledgeRetriever,
)
from insight_pipeline.adapters.organization_knowledge.in_memory_repository import (
    InMemoryOrganizationKnowledgeRepository,
)
from insight_pipeline.agents.investigation_planner.facade import InvestigationPlannerAgent
from insight_pipeline.prompts.registry import default_prompt_registry


def _hypothesis_package() -> HypothesisPackage:
    return HypothesisPackage(
        organization_id="org-1",
        hypothesis_statement="High performers show elevated burnout under ambiguous authority.",
        mechanism_explanation="Execution capability without decision rights concentrates load.",
        business_lens="skill_concentration",
        target_constructs=["burnout", "decision_rights"],
        scorecard=EvaluationScorecard(composite=0.7),
        critique=CritiqueResult(),
        search_stats=SearchStatistics(),
    )


async def test_investigation_planner_produces_a_plan():
    llm = MockLLMService()
    prompts = default_prompt_registry()
    engine = DirectLLMInvestigationPlanner(llm, prompts)
    retriever = EmbeddingOrganizationKnowledgeRetriever(
        InMemoryOrganizationKnowledgeRepository(), HashEmbeddingService()
    )
    agent = InvestigationPlannerAgent(engine, retriever)

    plan = await agent.run(_hypothesis_package())

    assert plan.hypothesis_package_id
    assert plan.organization_id == "org-1"
    assert plan.target_population is not None
    assert isinstance(plan.variables_required, list)


async def test_investigation_planner_works_with_empty_knowledge_base():
    llm = MockLLMService()
    prompts = default_prompt_registry()
    engine = DirectLLMInvestigationPlanner(llm, prompts)
    retriever = EmbeddingOrganizationKnowledgeRetriever(
        InMemoryOrganizationKnowledgeRepository(), HashEmbeddingService()
    )
    agent = InvestigationPlannerAgent(engine, retriever)

    plan = await agent.run(_hypothesis_package())
    assert plan.relevant_knowledge == []
