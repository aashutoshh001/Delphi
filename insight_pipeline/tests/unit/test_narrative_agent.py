from hypothesis_agent.adapters.llm.mock_llm_service import MockLLMService
from insight_pipeline.agents.narrative.facade import NarrativeAgent
from insight_pipeline.contracts.business_insight import BusinessFinding, BusinessInsights
from insight_pipeline.contracts.root_cause import RootCauseGraph
from insight_pipeline.plugins.narrative_strategies.balanced import BalancedNarrativeStrategy
from insight_pipeline.prompts.registry import default_prompt_registry


async def test_narrative_agent_produces_a_narrative():
    llm = MockLLMService()
    strategy = BalancedNarrativeStrategy(llm, default_prompt_registry())
    agent = NarrativeAgent(strategy)

    insights = BusinessInsights(findings=[BusinessFinding(statement="burnout concentrates in ICs")])
    root_cause = RootCauseGraph(potential_mechanisms=["overload"])

    narrative = await agent.run(insights, root_cause)

    assert narrative.executive_summary
    assert isinstance(narrative.storyline, list)
