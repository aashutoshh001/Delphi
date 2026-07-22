from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from hypothesis_agent.contracts.llm import LLMMessage, LLMRequest
from hypothesis_agent.contracts.memory import ReasoningTraceEntry
from hypothesis_agent.logging_setup import get_logger
from hypothesis_agent.reasoning.dependencies import AgentDependencies
from hypothesis_agent.reasoning.state import HypothesisSearchState

logger = get_logger("nodes.improve")

_IMPROVE_THRESHOLD = 0.75


class _ImproveResponse(BaseModel):
    statement: str
    mechanism: str


def make_improve_node(deps: AgentDependencies):
    async def improve(state: HypothesisSearchState) -> dict[str, Any]:
        candidate = state["current_candidate"]
        critique = candidate.critique
        composite = candidate.composite_score()

        needs_improvement = (
            critique is not None
            and critique.suggested_improvements
            and composite < _IMPROVE_THRESHOLD
        )
        if not needs_improvement:
            return {}

        template = deps.prompts.get("improve")
        rendered = template.render(
            narrative=state["organization_understanding"].narrative,
            statement=candidate.statement,
            mechanism=candidate.mechanism,
            issues="\n".join(f"- {i}" for i in critique.issues) or "(none)",
            suggestions="\n".join(f"- {s}" for s in critique.suggested_improvements),
        )
        request = LLMRequest(
            messages=[
                LLMMessage(role="system", content=rendered.system),
                LLMMessage(role="user", content=rendered.user),
            ],
            temperature=0.5,
        )
        result = await deps.llm_service.complete_structured(request, _ImproveResponse)

        # Note: the refined text is not re-scored/re-critiqued in this pass —
        # the scorecard computed upstream stands as an approximation. Looping
        # back through critique/scoring for the refined text is a reasonable
        # future enhancement, deliberately left out to keep the graph's edges
        # matching the documented reasoning workflow (§13 of the architecture doc).
        candidate = candidate.model_copy(
            update={"statement": result.statement, "mechanism": result.mechanism, "status": "improved"}
        )

        logger.info("improved candidate", extra={"extra_fields": {"composite": composite}})
        trace = state["reasoning_trace"] + [
            ReasoningTraceEntry(
                step="improve",
                iteration=state["iteration"],
                summary=f"Revised statement to address {len(critique.issues)} issue(s).",
            )
        ]
        return {"current_candidate": candidate, "reasoning_trace": trace}

    return improve

