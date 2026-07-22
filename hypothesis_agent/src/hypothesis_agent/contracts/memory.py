"""Memory-side contracts: historical hypotheses, feedback, and reasoning
traces. Defined so future memory backends have a target contract even though
no store exists yet — every repository built against these must behave
correctly when the backing store is empty."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from hypothesis_agent.contracts.hypothesis import (
        CritiqueResult,
        EvaluationScorecard,
        SearchStatistics,
    )


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FeedbackSummary(BaseModel):
    up_count: int = 0
    down_count: int = 0

    @property
    def total(self) -> int:
        return self.up_count + self.down_count


class HistoricalHypothesisRecord(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("hist"))
    organization_id: str | None = None
    headline: str = ""
    summary: str = ""
    statement: str
    mechanism: str = ""
    lens: str
    target_constructs: list[str] = Field(default_factory=list)
    embedding: list[float] | None = None
    scorecard: "EvaluationScorecard | None" = None
    critique: "CritiqueResult | None" = None
    search_stats: "SearchStatistics | None" = None
    feedback_summary: FeedbackSummary = Field(default_factory=FeedbackSummary)
    created_at: datetime = Field(default_factory=_utcnow)
    reasoning_path_ref: str | None = None


class FeedbackRecord(BaseModel):
    """One feedback event. `signal="none"` represents clearing a previously
    given reaction (the UI's toggle-off-on-repeat-click), not "no opinion" —
    there is no record for a hypothesis that was never reacted to."""

    id: str = Field(default_factory=lambda: _new_id("fb"))
    hypothesis_id: str
    organization_id: str | None = None
    lens: str | None = None
    signal: Literal["up", "down", "none"]
    user_ref: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    comment: str | None = None


class ReasoningTraceEntry(BaseModel):
    step: str
    iteration: int
    summary: str
    timestamp: datetime = Field(default_factory=_utcnow)
    metadata: dict = Field(default_factory=dict)
