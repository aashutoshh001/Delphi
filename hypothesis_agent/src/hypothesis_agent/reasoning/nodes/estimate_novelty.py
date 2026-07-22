from __future__ import annotations

from typing import Any

from hypothesis_agent.contracts.hypothesis import EvaluationScorecard
from hypothesis_agent.contracts.memory import ReasoningTraceEntry
from hypothesis_agent.logging_setup import get_logger
from hypothesis_agent.reasoning.dependencies import AgentDependencies
from hypothesis_agent.reasoning.nodes._evaluation_helpers import run_evaluators
from hypothesis_agent.reasoning.search.scoring import composite_score
from hypothesis_agent.reasoning.state import HypothesisSearchState

logger = get_logger("nodes.estimate_novelty")

_DIMENSIONS = ("novelty", "depth", "expected_insight", "confidence", "future_extensibility")


def make_estimate_novelty_node(deps: AgentDependencies):
    async def estimate_novelty(state: HypothesisSearchState) -> dict[str, Any]:
        candidate = state["current_candidate"]
        scores = await run_evaluators(deps, state, candidate, _DIMENSIONS)
        all_scores = {**state["partial_scores"], **scores}

        scorecard = EvaluationScorecard(
            **{dim: score.value for dim, score in all_scores.items()},
            dimension_notes={dim: score.rationale for dim, score in all_scores.items()},
        )
        scorecard.composite = composite_score(scorecard, deps.config.scoring.weights)
        candidate = candidate.model_copy(update={"scorecard": scorecard, "status": "scored"})

        logger.info("scored candidate", extra={"extra_fields": {"composite": scorecard.composite}})
        trace = state["reasoning_trace"] + [
            ReasoningTraceEntry(
                step="estimate_novelty",
                iteration=state["iteration"],
                summary=f"composite={scorecard.composite:.3f}",
            )
        ]
        return {"current_candidate": candidate, "reasoning_trace": trace}

    return estimate_novelty
