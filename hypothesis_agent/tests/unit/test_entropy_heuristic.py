import random

from hypothesis_agent.contracts.hypothesis import BusinessLens, EvaluationScorecard, HypothesisCandidate
from hypothesis_agent.plugins.search_heuristics.entropy_heuristic import (
    EntropyMaximizingHeuristic,
)

_LENSES = [
    BusinessLens(id="a", display_name="A", description="d"),
    BusinessLens(id="b", display_name="B", description="d"),
]


def test_choose_lens_favors_unexplored_lens_over_heavily_explored_one():
    heuristic = EntropyMaximizingHeuristic(exploration_floor=0.05, rng=random.Random(0))
    archive = [
        HypothesisCandidate(lens="a", statement=f"s{i}") for i in range(20)
    ]
    counts = {"a": 0, "b": 0}
    for _ in range(200):
        chosen = heuristic.choose_lens(_LENSES, archive, lens_priors={})
        counts[chosen.id] += 1
    assert counts["b"] > counts["a"]


def test_choose_lens_never_fully_excludes_a_lens_even_with_heavy_history():
    heuristic = EntropyMaximizingHeuristic(exploration_floor=0.1, rng=random.Random(1))
    archive = [HypothesisCandidate(lens="a", statement=f"s{i}") for i in range(100)]
    chosen_ids = {heuristic.choose_lens(_LENSES, archive, lens_priors={}).id for _ in range(500)}
    assert chosen_ids == {"a", "b"}


def test_should_discard_below_threshold():
    heuristic = EntropyMaximizingHeuristic(discard_threshold=0.4)
    weak = HypothesisCandidate(
        lens="a", statement="s", scorecard=EvaluationScorecard(composite=0.2)
    )
    strong = HypothesisCandidate(
        lens="a", statement="s", scorecard=EvaluationScorecard(composite=0.8)
    )
    assert heuristic.should_discard(weak) is True
    assert heuristic.should_discard(strong) is False


def test_should_discard_false_when_unscored():
    heuristic = EntropyMaximizingHeuristic()
    candidate = HypothesisCandidate(lens="a", statement="s")
    assert heuristic.should_discard(candidate) is False
