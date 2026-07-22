from __future__ import annotations

from hypothesis_agent.contracts.memory import FeedbackRecord, FeedbackSummary
from hypothesis_agent.ports.feedback_repository import FeedbackRepository


class InMemoryFeedbackRepository(FeedbackRepository):
    def __init__(self) -> None:
        self._records: list[FeedbackRecord] = []

    async def get_lens_feedback_counts(
        self, organization_id: str | None
    ) -> dict[str, FeedbackSummary]:
        counts: dict[str, FeedbackSummary] = {}
        for record in self._records:
            if not record.lens:
                continue
            if organization_id is not None and record.organization_id not in (
                None,
                organization_id,
            ):
                continue
            summary = counts.setdefault(record.lens, FeedbackSummary())
            if record.signal == "up":
                summary.up_count += 1
            elif record.signal == "down":
                summary.down_count += 1
            # "none" clears a reaction; it contributes to neither count.
        return counts

    async def record_feedback(self, record: FeedbackRecord) -> None:
        self._records.append(record)
