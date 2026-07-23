"""Analytics Agent contracts — see docs/PLATFORM_ARCHITECTURE.md §9."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class AnalysisMethodResult(BaseModel):
    method: str
    variables_involved: list[str] = Field(default_factory=list)
    statistic: float | None = None
    p_value: float | None = None
    effect_size: float | None = None
    confidence_interval: tuple[float, float] | None = None
    interpretation_notes: str = ""
    caveats: list[str] = Field(default_factory=list)


class AnalyticsResult(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("analytics"))
    investigation_plan_id: str
    dataset_id: str
    methods_run: list[AnalysisMethodResult] = Field(default_factory=list)
    data_quality_notes: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
