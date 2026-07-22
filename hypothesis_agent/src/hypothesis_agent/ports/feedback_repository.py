from abc import ABC, abstractmethod

from hypothesis_agent.contracts.memory import FeedbackRecord, FeedbackSummary


class FeedbackRepository(ABC):
    """Store of user thumbs-up/down signals. Exposes only aggregate counts per
    lens category — never row-level feedback or hard-learned weights. Turning
    counts into priors is a FeedbackPriorPolicy concern, not this port's.
    Must behave correctly against an empty store (no feedback yet)."""

    @abstractmethod
    async def get_lens_feedback_counts(
        self, organization_id: str | None
    ) -> dict[str, FeedbackSummary]: ...

    @abstractmethod
    async def record_feedback(self, record: FeedbackRecord) -> None: ...
