from hypothesis_agent.contracts.hypothesis import EvaluationScorecard, HypothesisCandidate
from hypothesis_agent.reasoning.search.scoring import composite_score
from hypothesis_agent.reasoning.search.stopping import StoppingCriteria


def _candidate(score: float) -> HypothesisCandidate:
    return HypothesisCandidate(lens="a", statement="s", scorecard=EvaluationScorecard(composite=score))


def test_stops_at_max_iterations():
    criteria = StoppingCriteria(max_iterations=3, convergence_window=10, convergence_epsilon=0.0)
    should_stop, reason = criteria.should_stop(iteration=3, archive=[])
    assert should_stop is True
    assert reason == "max_iterations_reached"


def test_continues_before_max_iterations_with_insufficient_history():
    criteria = StoppingCriteria(max_iterations=10, convergence_window=3, convergence_epsilon=0.01)
    should_stop, reason = criteria.should_stop(iteration=2, archive=[_candidate(0.5)])
    assert should_stop is False
    assert reason == "continue"


def test_converges_when_recent_scores_plateau():
    criteria = StoppingCriteria(max_iterations=20, convergence_window=2, convergence_epsilon=0.05)
    archive = [_candidate(0.9), _candidate(0.3), _candidate(0.91), _candidate(0.90)]
    should_stop, reason = criteria.should_stop(iteration=4, archive=archive)
    assert should_stop is True
    assert reason == "converged"


def test_does_not_converge_when_still_improving():
    criteria = StoppingCriteria(max_iterations=20, convergence_window=2, convergence_epsilon=0.05)
    archive = [_candidate(0.2), _candidate(0.3), _candidate(0.4), _candidate(0.9)]
    should_stop, reason = criteria.should_stop(iteration=4, archive=archive)
    assert should_stop is False


def test_composite_score_is_weighted_sum():
    scorecard = EvaluationScorecard(business_value=1.0, novelty=0.0)
    weights = {"business_value": 0.6, "novelty": 0.4}
    assert composite_score(scorecard, weights) == 0.6
