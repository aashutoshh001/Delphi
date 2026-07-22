from __future__ import annotations

from hypothesis_agent.contracts.hypothesis import EVALUATION_DIMENSIONS, EvaluationScorecard


def composite_score(scorecard: EvaluationScorecard, weights: dict[str, float]) -> float:
    dims = scorecard.as_dimension_map()
    return sum(dims[d] * weights.get(d, 0.0) for d in EVALUATION_DIMENSIONS)
