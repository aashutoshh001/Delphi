"""Data Retrieval contracts — see docs/PLATFORM_ARCHITECTURE.md §2, §8.

`DatasetHandle` is an opaque reference, never raw rows. Only adapter-internal
code (inside Analytics plugins and the Plot Generation Tool's data resolver)
resolves a handle into an actual in-memory table — the same "reasoning never
touches the raw table" boundary the Hypothesis Agent already enforces for
`EmployeeDataLandscape`, applied one stage later where using the data
(not just describing it) becomes unavoidable."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from hypothesis_agent.contracts.organization import AttributeField


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class DatasetHandle(BaseModel):
    backend: str
    location: str
    row_count: int
    # Column *names* only — schema metadata, not data, so safe at this layer.
    # Lets DatasetRetriever build accurate DatasetMetadata even when a
    # repository falls back to a wider table than was actually requested.
    columns: list[str] = Field(default_factory=list)
    resolved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DatasetMetadata(BaseModel):
    fields: list[AttributeField] = Field(default_factory=list)
    population_description: str = ""
    coverage_notes: str = ""


class RetrievedDataset(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("dataset"))
    investigation_plan_id: str
    handle: DatasetHandle
    metadata: DatasetMetadata
    retrieval_query_summary: str = ""


class RetrievalQuery(BaseModel):
    """What `QueryPlanner.plan()` produces and `DatasetRetriever` consumes —
    the mapping from InvestigationPlan variables onto actual available
    fields, plus filters/segmentation resolved against real schema."""

    organization_id: str
    requested_fields: list[str] = Field(default_factory=list)
    filters: list[str] = Field(default_factory=list)
    segmentation: list[str] = Field(default_factory=list)
    notes: str = ""
