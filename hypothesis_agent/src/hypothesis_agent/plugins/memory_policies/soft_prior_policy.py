from __future__ import annotations

from hypothesis_agent.contracts.memory import FeedbackSummary
from hypothesis_agent.plugins.memory_policies.base import FeedbackPriorPolicy


class SoftPriorPolicy(FeedbackPriorPolicy):
    """Laplace-smoothed up/down ratio per lens, mapped into a bounded
    multiplier range. Zero feedback -> ratio 0.5 -> multiplier 1.0 (uniform).
    A single vote can't push a lens near the bounds; only sustained signal can."""

    def __init__(
        self,
        min_multiplier: float = 0.7,
        max_multiplier: float = 1.3,
        smoothing: float = 3.0,
    ) -> None:
        if not 0.0 < min_multiplier <= 1.0 <= max_multiplier:
            raise ValueError("expected min_multiplier <= 1.0 <= max_multiplier")
        self._min = min_multiplier
        self._max = max_multiplier
        self._smoothing = smoothing

    def compute_lens_priors(self, counts: dict[str, FeedbackSummary]) -> dict[str, float]:
        priors: dict[str, float] = {}
        for lens_id, summary in counts.items():
            ratio = (summary.up_count + self._smoothing) / (
                summary.total + 2 * self._smoothing
            )
            priors[lens_id] = self._min + (self._max - self._min) * ratio
        return priors
