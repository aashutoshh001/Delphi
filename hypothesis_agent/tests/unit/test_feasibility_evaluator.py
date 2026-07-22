import pytest

from hypothesis_agent.contracts.hypothesis import HypothesisCandidate
from hypothesis_agent.contracts.organization import OrganizationUnderstanding
from hypothesis_agent.plugins.evaluators.base import EvaluationContext
from hypothesis_agent.plugins.evaluators.feasibility_evaluator import (
    FeasibilityFromLandscapeEvaluator,
)


def _context(categories: set[str]) -> EvaluationContext:
    understanding = OrganizationUnderstanding(organization_id="org-1", narrative="n")
    return EvaluationContext(understanding=understanding, landscape_categories=categories, archive=[])


@pytest.mark.asyncio
async def test_feasibility_high_when_constructs_covered():
    evaluator = FeasibilityFromLandscapeEvaluator()
    candidate = HypothesisCandidate(lens="a", statement="s", target_constructs=["burnout", "performance"])
    score = await evaluator.evaluate(candidate, _context({"burnout", "performance"}))
    assert score.value > 0.6


@pytest.mark.asyncio
async def test_feasibility_low_when_constructs_uncovered():
    evaluator = FeasibilityFromLandscapeEvaluator()
    candidate = HypothesisCandidate(lens="a", statement="s", target_constructs=["quantum_readiness"])
    score = await evaluator.evaluate(candidate, _context({"burnout", "performance"}))
    assert score.value < 0.4


@pytest.mark.asyncio
async def test_feasibility_never_reaches_one_even_with_full_coverage():
    evaluator = FeasibilityFromLandscapeEvaluator()
    candidate = HypothesisCandidate(lens="a", statement="s", target_constructs=["burnout"])
    score = await evaluator.evaluate(candidate, _context({"burnout"}))
    assert score.value < 1.0
