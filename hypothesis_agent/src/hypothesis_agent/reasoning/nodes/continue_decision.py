from __future__ import annotations

from typing import Any, Literal

from hypothesis_agent.contracts.memory import ReasoningTraceEntry
from hypothesis_agent.logging_setup import get_logger
from hypothesis_agent.reasoning.dependencies import AgentDependencies
from hypothesis_agent.reasoning.search.frontier import best_of
from hypothesis_agent.reasoning.search.stopping import StoppingCriteria
from hypothesis_agent.reasoning.state import HypothesisSearchState

logger = get_logger("nodes.continue_decision")


def make_continue_decision_node(deps: AgentDependencies):
    stopping = StoppingCriteria(
        max_iterations=deps.config.search.max_iterations,
        convergence_window=deps.config.search.convergence_window,
        convergence_epsilon=deps.config.search.convergence_epsilon,
    )

    async def continue_decision(state: HypothesisSearchState) -> dict[str, Any]:
        candidate = state["current_candidate"]
        discard = deps.plugins.search_heuristic.should_discard(candidate)
        if discard:
            candidate = candidate.model_copy(update={"status": "rejected"})

        archive = state["archive"] + [candidate]
        frontier = [c for c in archive if c.status != "rejected"]
        best = best_of(archive)
        next_iteration = state["iteration"] + 1
        should_stop, reason = stopping.should_stop(next_iteration, archive)
        termination_reason = reason if should_stop else "continue"

        logger.info(
            "continue decision",
            extra={"extra_fields": {"discarded": discard, "termination_reason": termination_reason}},
        )
        trace = state["reasoning_trace"] + [
            ReasoningTraceEntry(
                step="continue_decision",
                iteration=state["iteration"],
                summary=f"discarded={discard}, decision={termination_reason}",
            )
        ]
        return {
            "archive": archive,
            "frontier": frontier,
            "best_candidate": best,
            "iteration": next_iteration,
            "termination_reason": termination_reason,
            "reasoning_trace": trace,
        }

    return continue_decision


def route_after_continue_decision(state: HypothesisSearchState) -> Literal["continue", "finalize"]:
    return "continue" if state.get("termination_reason") == "continue" else "finalize"
