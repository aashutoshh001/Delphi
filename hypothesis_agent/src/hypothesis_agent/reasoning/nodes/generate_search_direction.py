from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from hypothesis_agent.contracts.hypothesis import SearchDirective
from hypothesis_agent.contracts.llm import LLMMessage, LLMRequest
from hypothesis_agent.contracts.memory import ReasoningTraceEntry
from hypothesis_agent.logging_setup import get_logger
from hypothesis_agent.reasoning.dependencies import AgentDependencies
from hypothesis_agent.reasoning.search.frontier import explored_lens_summary
from hypothesis_agent.reasoning.state import HypothesisSearchState

logger = get_logger("nodes.generate_search_direction")


class _DirectiveResponse(BaseModel):
    guiding_question: str
    target_constructs: list[str] = Field(default_factory=list)
    rationale: str


def make_generate_search_direction_node(deps: AgentDependencies):
    async def generate_search_direction(state: HypothesisSearchState) -> dict[str, Any]:
        archive = state["archive"]
        lenses = list(deps.plugins.lenses.all().values())
        heuristic = deps.plugins.search_heuristic

        lens = heuristic.choose_lens(lenses, archive, state["lens_priors"])
        parent = heuristic.choose_expansion_parent(archive)

        template = deps.prompts.get("generate_search_direction")
        rendered = template.render(
            narrative=state["organization_understanding"].narrative,
            lens_name=lens.display_name,
            lens_description=lens.description,
            seed_questions="\n".join(f"- {q}" for q in lens.seed_questions),
            explored_summary=explored_lens_summary(archive),
        )
        request = LLMRequest(
            messages=[
                LLMMessage(role="system", content=rendered.system),
                LLMMessage(role="user", content=rendered.user),
            ],
            temperature=0.6,
        )
        result = await deps.llm_service.complete_structured(request, _DirectiveResponse)

        directive = SearchDirective(
            lens=lens.id,
            guiding_question=result.guiding_question,
            target_constructs=result.target_constructs,
            rationale=result.rationale,
            parent_candidate_id=parent.id if parent else None,
        )

        logger.info(
            "chose search direction",
            extra={"extra_fields": {"lens": lens.id, "mutation": parent is not None}},
        )
        trace = state["reasoning_trace"] + [
            ReasoningTraceEntry(
                step="generate_search_direction",
                iteration=state["iteration"],
                summary=f"Lens '{lens.id}': {result.guiding_question}",
            )
        ]
        return {"current_directive": directive, "reasoning_trace": trace}

    return generate_search_direction
