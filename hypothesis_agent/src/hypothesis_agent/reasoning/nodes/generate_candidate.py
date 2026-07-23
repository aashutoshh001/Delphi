from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from hypothesis_agent.contracts.hypothesis import HypothesisCandidate
from hypothesis_agent.contracts.llm import LLMMessage, LLMRequest
from hypothesis_agent.contracts.memory import ReasoningTraceEntry
from hypothesis_agent.logging_setup import get_logger
from hypothesis_agent.reasoning.dependencies import AgentDependencies
from hypothesis_agent.reasoning.observability import session_metadata
from hypothesis_agent.reasoning.state import HypothesisSearchState

logger = get_logger("nodes.generate_candidate")


class _CandidateResponse(BaseModel):
    statement: str
    mechanism: str
    target_constructs: list[str] = Field(default_factory=list)
    proposed_population: str | None = None


def make_generate_candidate_node(deps: AgentDependencies):
    async def generate_candidate(state: HypothesisSearchState) -> dict[str, Any]:
        directive = state["current_directive"]
        avoid_summary = "\n".join(f"- {c.statement}" for c in state["archive"][-5:]) or "(none yet)"

        template = deps.prompts.get("generate_candidate")
        rendered = template.render(
            narrative=state["organization_understanding"].narrative,
            lens_name=directive.lens,
            guiding_question=directive.guiding_question,
            rationale=directive.rationale,
            avoid_summary=avoid_summary,
        )
        request = LLMRequest(
            messages=[
                LLMMessage(role="system", content=rendered.system),
                LLMMessage(role="user", content=rendered.user),
            ],
            temperature=0.8,
            metadata=session_metadata(state.get("session_id")),
        )
        result = await deps.llm_service.complete_structured(request, _CandidateResponse)

        target_constructs = result.target_constructs or directive.target_constructs
        embedding = await deps.embedding_service.embed(f"{result.statement} {result.mechanism}")

        candidate = HypothesisCandidate(
            iteration=state["iteration"],
            parent_id=directive.parent_candidate_id,
            lens=directive.lens,
            statement=result.statement,
            mechanism=result.mechanism,
            target_constructs=target_constructs,
            proposed_population=result.proposed_population,
            embedding=embedding,
            reasoning_trace=[directive.rationale],
            status="proposed",
        )

        logger.info("generated candidate", extra={"extra_fields": {"lens": directive.lens}})
        trace = state["reasoning_trace"] + [
            ReasoningTraceEntry(
                step="generate_candidate",
                iteration=state["iteration"],
                summary=result.statement,
            )
        ]
        return {"current_candidate": candidate, "reasoning_trace": trace}

    return generate_candidate
