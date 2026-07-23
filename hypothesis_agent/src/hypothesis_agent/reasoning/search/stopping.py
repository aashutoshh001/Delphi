from __future__ import annotations

from hypothesis_agent.contracts.hypothesis import HypothesisCandidate


class StoppingCriteria:
    """Stops the search when either the best score has plateaued over a
    trailing window, or the iteration budget is exhausted. Both bounds are
    config-driven, never hardcoded."""

    def __init__(self, max_iterations: int, convergence_window: int, convergence_epsilon: float) -> None:
        self._max_iterations = max_iterations
        self._window = convergence_window
        self._epsilon = convergence_epsilon

    def should_stop(
        self, iteration: int, archive: list[HypothesisCandidate]
    ) -> tuple[bool, str]:
        if iteration >= self._max_iterations:
            return True, "max_iterations_reached"

        # Only viable candidates count toward convergence — a plateau made of
        # rejected near-duplicates isn't real convergence, it's the search
        # spinning on an already-covered region (see frontier.best_of, which
        # applies the same "rejected is never eligible" filter for picking
        # the winner).
        scored = [
            c.composite_score()
            for c in archive
            if c.scorecard is not None and c.status != "rejected"
        ]
        if len(scored) < self._window + 1:
            return False, "continue"

        recent_best = max(scored[-self._window :])
        prior_best = max(scored[: -self._window])
        if recent_best - prior_best < self._epsilon:
            return True, "converged"

        return False, "continue"
