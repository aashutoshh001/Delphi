"""Root-cause strategy backed by Deep Agents — the flagship use case in this
whole pipeline (docs/PLATFORM_ARCHITECTURE.md §10/§17). Open-ended,
multi-angle mechanism exploration over an organizational system benefits
from sub-agent delegation: one angle explores mediators, one checks
alternative/confounding explanations, one checks consistency against
Organization Knowledge, a final pass assembles the graph. Requires Python
>=3.11 — falls back to LLMMechanismBrainstormPlugin when unavailable."""

from __future__ import annotations

from hypothesis_agent.contracts.llm import LLMMessage, LLMRequest
from hypothesis_agent.ports.llm_service import LLMService
from insight_pipeline.contracts.analytics import AnalyticsResult
from insight_pipeline.contracts.investigation import InvestigationPlan
from insight_pipeline.contracts.organization_knowledge import OrganizationKnowledge
from insight_pipeline.contracts.root_cause import RootCauseGraph
from insight_pipeline.plugins.root_cause_strategies.base import RootCauseStrategyPlugin
from insight_pipeline.plugins.root_cause_strategies.llm_mechanism_brainstorm import (
    RootCauseResponse,
    render_analytics,
)


def _extract_last_message_text(result: dict) -> str:
    messages = result.get("messages", [])
    if not messages:
        return ""
    last = messages[-1]
    content = getattr(last, "content", None)
    if content is None and isinstance(last, dict):
        content = last.get("content")
    return content or ""


class DeepAgentMechanismBrainstormPlugin(RootCauseStrategyPlugin):
    strategy_name = "deep_agent_mechanism_brainstorm"

    def __init__(self, llm_service: LLMService, deep_agent_model: str = "openai:gpt-4.1-mini") -> None:
        try:
            from deepagents import create_deep_agent
        except ImportError as exc:
            raise ImportError(
                "DeepAgentMechanismBrainstormPlugin requires the 'deepagents' package: "
                "install insight_pipeline[deep-agents] (Python >=3.11)"
            ) from exc
        self._create_deep_agent = create_deep_agent
        self._deep_agent_model = deep_agent_model
        self._llm = llm_service

    async def discover(
        self,
        plan: InvestigationPlan,
        analytics: AnalyticsResult,
        knowledge: list[OrganizationKnowledge],
    ) -> RootCauseGraph:
        analytics_text = render_analytics(analytics)
        knowledge_text = "\n".join(f"- [{k.category}] {k.title}: {k.excerpt}" for k in knowledge)

        def get_analytics_results() -> str:
            """Return the statistical analysis results to explain."""
            return analytics_text

        def get_relevant_organizational_knowledge() -> str:
            """Return relevant organizational policy/culture knowledge, if any."""
            return knowledge_text or "(none available)"

        agent = self._create_deep_agent(
            model=self._deep_agent_model,
            tools=[get_analytics_results, get_relevant_organizational_knowledge],
            system_prompt=(
                "You are an organizational root-cause analyst. Explore "
                "mediators, moderators, alternative explanations, and "
                "consistency with organizational knowledge separately, then "
                "assemble a causal graph (drivers, mediators, moderators, "
                "outcomes, bottlenecks) explaining the analytics results. "
                "Always propose alternative explanations — confounding and "
                "reverse causality are real risks."
            ),
        )
        result = await agent.ainvoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": f"Explain these results: {'; '.join(plan.statistical_questions)}",
                    }
                ]
            }
        )
        notes = _extract_last_message_text(result)

        extraction_request = LLMRequest(
            messages=[
                LLMMessage(
                    role="system",
                    content="Extract a structured causal graph from the analyst's notes below.",
                ),
                LLMMessage(role="user", content=f"Analyst notes:\n{notes}"),
            ],
            temperature=0.0,
            metadata={"session_id": plan.hypothesis_package_id} if plan.hypothesis_package_id else {},
        )
        extracted = await self._llm.complete_structured(extraction_request, RootCauseResponse)
        return RootCauseGraph(
            nodes=extracted.nodes,
            edges=extracted.edges,
            potential_mechanisms=extracted.potential_mechanisms,
            supporting_evidence=extracted.supporting_evidence,
            alternative_explanations=extracted.alternative_explanations,
            confidence=extracted.confidence,
        )
