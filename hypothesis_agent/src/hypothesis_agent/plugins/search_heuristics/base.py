from abc import ABC, abstractmethod

from hypothesis_agent.contracts.hypothesis import BusinessLens, HypothesisCandidate


class SearchHeuristic(ABC):
    """Governs which region of hypothesis space gets explored next. Owns the
    High Entropy Requirement: it must not let the search repeatedly settle on
    the same lens/constructs."""

    @abstractmethod
    def choose_lens(
        self,
        available_lenses: list[BusinessLens],
        archive: list[HypothesisCandidate],
        lens_priors: dict[str, float],
    ) -> BusinessLens: ...

    @abstractmethod
    def choose_expansion_parent(
        self, archive: list[HypothesisCandidate]
    ) -> HypothesisCandidate | None:
        """Optionally pick a promising archived candidate to mutate/refine
        instead of starting a fresh lens. Returning None means "start fresh"."""
        ...

    @abstractmethod
    def should_discard(self, candidate: HypothesisCandidate) -> bool: ...
