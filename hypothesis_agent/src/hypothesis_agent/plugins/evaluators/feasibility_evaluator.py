"""Rule-based evaluator: scores feasibility from the employee data landscape
alone, no LLM call. Demonstrates that Evaluator plugins need not be LLM-backed."""

from __future__ import annotations

from hypothesis_agent.contracts.hypothesis import DimensionScore, HypothesisCandidate
from hypothesis_agent.plugins.evaluators.base import EvaluationContext, Evaluator


class FeasibilityFromLandscapeEvaluator(Evaluator):
    dimension = "feasibility"

    async def evaluate(
        self, candidate: HypothesisCandidate, context: EvaluationContext
    ) -> DimensionScore:
        constructs = {c.lower() for c in candidate.target_constructs}
        categories = {c.lower() for c in context.landscape_categories}
        if not constructs:
            return DimensionScore(
                dimension=self.dimension,
                value=0.3,
                rationale="No target constructs specified; feasibility unknown.",
                evaluator="feasibility_from_landscape",
            )
        covered = sum(1 for c in constructs if any(c in cat or cat in c for cat in categories))
        ratio = covered / len(constructs)
        # Even with a perfect landscape match, cap below 1.0 — landscape only
        # describes *what exists*, not whether coverage/quality is sufficient.
        value = min(0.9, 0.2 + 0.7 * ratio)
        return DimensionScore(
            dimension=self.dimension,
            value=value,
            rationale=f"{covered}/{len(constructs)} target constructs map onto known data categories.",
            evaluator="feasibility_from_landscape",
        )
