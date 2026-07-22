from abc import ABC, abstractmethod

from hypothesis_agent.contracts.memory import FeedbackSummary


class FeedbackPriorPolicy(ABC):
    """Turns raw per-lens feedback counts into soft multiplicative priors that
    bias — but never eliminate — exploration of a lens. Not hard learning:
    no weights are trained, nothing is permanently excluded."""

    @abstractmethod
    def compute_lens_priors(self, counts: dict[str, FeedbackSummary]) -> dict[str, float]: ...
