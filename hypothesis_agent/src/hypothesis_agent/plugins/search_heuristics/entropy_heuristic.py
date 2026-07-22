"""Default SearchHeuristic: maximizes diversity over explored lenses while
still respecting soft feedback priors (High Entropy Requirement + soft
priors, never mode collapse)."""

from __future__ import annotations

import random
from collections import Counter

from hypothesis_agent.contracts.hypothesis import BusinessLens, HypothesisCandidate
from hypothesis_agent.plugins.search_heuristics.base import SearchHeuristic


class EntropyMaximizingHeuristic(SearchHeuristic):
    def __init__(
        self,
        exploration_floor: float = 0.15,
        mutation_probability: float = 0.2,
        discard_threshold: float = 0.35,
        expansion_min_score: float = 0.6,
        max_children_per_parent: int = 2,
        rng: random.Random | None = None,
    ) -> None:
        self._exploration_floor = exploration_floor
        self._mutation_probability = mutation_probability
        self._discard_threshold = discard_threshold
        self._expansion_min_score = expansion_min_score
        self._max_children = max_children_per_parent
        self._rng = rng or random.Random()

    def choose_lens(
        self,
        available_lenses: list[BusinessLens],
        archive: list[HypothesisCandidate],
        lens_priors: dict[str, float],
    ) -> BusinessLens:
        if not available_lenses:
            raise ValueError("choose_lens requires at least one available lens")
        usage = Counter(c.lens for c in archive)
        weights: list[float] = []
        for lens in available_lenses:
            prior = lens_priors.get(lens.id, 1.0)
            freshness = 1.0 / (1 + usage[lens.id])
            weights.append(self._exploration_floor + prior * freshness)
        return self._rng.choices(available_lenses, weights=weights, k=1)[0]

    def choose_expansion_parent(
        self, archive: list[HypothesisCandidate]
    ) -> HypothesisCandidate | None:
        if self._rng.random() > self._mutation_probability:
            return None
        children_count = Counter(c.parent_id for c in archive if c.parent_id)
        eligible = [
            c
            for c in archive
            if c.scorecard is not None
            and c.composite_score() >= self._expansion_min_score
            and children_count[c.id] < self._max_children
        ]
        if not eligible:
            return None
        return max(eligible, key=lambda c: c.composite_score())

    def should_discard(self, candidate: HypothesisCandidate) -> bool:
        # Near-duplicates are discarded unconditionally, regardless of score —
        # this is the hard half of the dedup guarantee (§ "High Entropy
        # Requirement" is about lens diversity, not about tolerating
        # near-identical restatements of an existing hypothesis).
        if candidate.critique and candidate.critique.similar_to_prior:
            return True
        if candidate.scorecard is None:
            return False
        if candidate.composite_score() < self._discard_threshold:
            return True
        if candidate.critique and candidate.critique.is_obvious and candidate.composite_score() < 0.6:
            return True
        return False
