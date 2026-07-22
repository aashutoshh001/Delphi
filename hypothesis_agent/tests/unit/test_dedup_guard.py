from hypothesis_agent.contracts.hypothesis import CritiqueResult, EvaluationScorecard, HypothesisCandidate
from hypothesis_agent.plugins.search_heuristics.entropy_heuristic import (
    EntropyMaximizingHeuristic,
)
from hypothesis_agent.reasoning.search.frontier import best_of


def test_should_discard_true_for_flagged_near_duplicate_regardless_of_score():
    heuristic = EntropyMaximizingHeuristic(discard_threshold=0.0)
    candidate = HypothesisCandidate(
        lens="a",
        statement="s",
        scorecard=EvaluationScorecard(composite=0.99),
        critique=CritiqueResult(similar_to_prior=True),
    )
    assert heuristic.should_discard(candidate) is True


def test_best_of_never_returns_a_rejected_candidate():
    weak_but_rejected = HypothesisCandidate(
        lens="a", statement="dup", scorecard=EvaluationScorecard(composite=0.95), status="rejected"
    )
    viable = HypothesisCandidate(
        lens="a", statement="ok", scorecard=EvaluationScorecard(composite=0.5), status="scored"
    )
    best = best_of([weak_but_rejected, viable])
    assert best is not None
    assert best.id == viable.id


def test_best_of_returns_none_when_everything_is_rejected():
    rejected = HypothesisCandidate(
        lens="a", statement="dup", scorecard=EvaluationScorecard(composite=0.9), status="rejected"
    )
    assert best_of([rejected]) is None
