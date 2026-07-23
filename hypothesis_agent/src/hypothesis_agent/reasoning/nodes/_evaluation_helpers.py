from __future__ import annotations

import asyncio

from hypothesis_agent.contracts.hypothesis import DimensionScore, HypothesisCandidate
from hypothesis_agent.plugins.evaluators.base import EvaluationContext
from hypothesis_agent.reasoning.dependencies import AgentDependencies
from hypothesis_agent.reasoning.state import HypothesisSearchState


async def run_evaluators(
    deps: AgentDependencies,
    state: HypothesisSearchState,
    candidate: HypothesisCandidate,
    dimensions: tuple[str, ...],
) -> dict[str, DimensionScore]:
    context = EvaluationContext(
        understanding=state["organization_understanding"],
        landscape_categories=state["data_landscape"].categories(),
        archive=state["archive"],
        session_id=state.get("session_id"),
    )
    # Each dimension's evaluator is independent (reads the same immutable
    # context, no shared mutation) — run them concurrently rather than
    # paying N sequential LLM round-trips per node.
    evaluators = [deps.plugins.evaluators.get(dimension) for dimension in dimensions]
    results = await asyncio.gather(*(e.evaluate(candidate, context) for e in evaluators))
    return dict(zip(dimensions, results))
