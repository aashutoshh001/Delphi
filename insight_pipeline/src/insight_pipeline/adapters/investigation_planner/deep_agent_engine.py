"""InvestigationPlannerEngine backed by LangChain Deep Agents: planning +
sub-task breakdown (variables, population, confounders, validation strategy
are semi-independent sub-problems) before any data has been touched — the
pipeline's second "gather and synthesize" step, same shape as
hypothesis_agent's DeepAgentUnderstandingEngine for understand_organization.

Requires Python >=3.11 (the `deepagents` package's own constraint) — falls
back to DirectLLMInvestigationPlanner when unavailable, same graceful-
degradation discipline as the Hypothesis Agent."""

from __future__ import annotations

from hypothesis_agent.contracts.hypothesis import HypothesisPackage
from hypothesis_agent.contracts.llm import LLMMessage, LLMRequest
from hypothesis_agent.ports.llm_service import LLMService
from insight_pipeline.adapters.investigation_planner.direct_llm_engine import InvestigationPlanResponse
from insight_pipeline.contracts.investigation import InvestigationPlan
from insight_pipeline.contracts.organization_knowledge import OrganizationKnowledge
from insight_pipeline.ports.investigation_planner_engine import InvestigationPlannerEngine


def _extract_last_message_text(result: dict) -> str:
    messages = result.get("messages", [])
    if not messages:
        return ""
    last = messages[-1]
    content = getattr(last, "content", None)
    if content is None and isinstance(last, dict):
        content = last.get("content")
    return content or ""


class DeepAgentInvestigationPlanner(InvestigationPlannerEngine):
    engine_name = "deep_agent"

    def __init__(self, llm_service: LLMService, deep_agent_model: str = "openai:gpt-4.1-mini") -> None:
        try:
            from deepagents import create_deep_agent
        except ImportError as exc:
            raise ImportError(
                "DeepAgentInvestigationPlanner requires the 'deepagents' package: "
                "install insight_pipeline[deep-agents] (Python >=3.11)"
            ) from exc
        self._create_deep_agent = create_deep_agent
        self._deep_agent_model = deep_agent_model
        self._llm = llm_service

    async def plan(
        self, hypothesis_package: HypothesisPackage, relevant_knowledge: list[OrganizationKnowledge]
    ) -> InvestigationPlan:
        hypothesis_json = hypothesis_package.model_dump_json(indent=2)
        knowledge_json = "\n".join(f"- [{k.category}] {k.title}: {k.excerpt}" for k in relevant_knowledge)

        def get_hypothesis() -> str:
            """Return the full hypothesis package to investigate."""
            return hypothesis_json

        def get_relevant_organizational_knowledge() -> str:
            """Return relevant organizational policy/culture knowledge, if any."""
            return knowledge_json or "(none available)"

        agent = self._create_deep_agent(
            model=self._deep_agent_model,
            tools=[get_hypothesis, get_relevant_organizational_knowledge],
            system_prompt=(
                "You are an investigation planner for a people-analytics "
                "consulting engagement. Break the hypothesis down into: "
                "required variables, target population, confounders, "
                "filtering rules, validation strategy, and recommended "
                "analysis types. You do not access data yourself."
            ),
        )
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": "Produce the investigation plan."}]}
        )
        notes = _extract_last_message_text(result)

        extraction_request = LLMRequest(
            messages=[
                LLMMessage(
                    role="system",
                    content="Extract the requested fields from the analyst's notes. Do not invent information the notes don't support.",
                ),
                LLMMessage(role="user", content=f"Analyst notes:\n{notes}"),
            ],
            temperature=0.0,
        )
        extracted = await self._llm.complete_structured(extraction_request, InvestigationPlanResponse)
        return InvestigationPlan(
            hypothesis_package_id=hypothesis_package.package_id,
            organization_id=hypothesis_package.organization_id,
            variables_required=extracted.variables_required,
            target_population=extracted.target_population,
            segmentation_strategy=extracted.segmentation_strategy,
            potential_confounders=extracted.potential_confounders,
            filtering_rules=extracted.filtering_rules,
            statistical_questions=extracted.statistical_questions,
            business_questions=extracted.business_questions,
            validation_strategy=extracted.validation_strategy,
            recommended_analysis_types=extracted.recommended_analysis_types,
            potential_risks=extracted.potential_risks,
            suggested_visualizations=extracted.suggested_visualizations,
            relevant_knowledge=relevant_knowledge,
            provenance={"engine": self.engine_name},
        )
