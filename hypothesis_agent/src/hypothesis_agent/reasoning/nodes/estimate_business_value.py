from __future__ import annotations

from typing import Any

from hypothesis_agent.contracts.memory import ReasoningTraceEntry
from hypothesis_agent.logging_setup import get_logger
from hypothesis_agent.reasoning.dependencies import AgentDependencies
from hypothesis_agent.reasoning.nodes._evaluation_helpers import run_evaluators
from hypothesis_agent.reasoning.state import HypothesisSearchState

logger = get_logger("nodes.estimate_business_value")

_DIMENSIONS = (
    "business_value",
    "strategic_importance",
    "actionability",
    "organizational_impact",
    "feasibility",
)


def make_estimate_business_value_node(deps: AgentDependencies):
    async def estimate_business_value(state: HypothesisSearchState) -> dict[str, Any]:
        candidate = state["current_candidate"]
        scores = await run_evaluators(deps, state, candidate, _DIMENSIONS)

        logger.info("scored business-value dimensions", extra={"extra_fields": {"dims": list(scores)}})
        trace = state["reasoning_trace"] + [
            ReasoningTraceEntry(
                step="estimate_business_value",
                iteration=state["iteration"],
                summary=", ".join(f"{d}={s.value:.2f}" for d, s in scores.items()),
            )
        ]
        return {"partial_scores": scores, "reasoning_trace": trace}

    return estimate_business_value
