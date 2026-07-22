"""Organization-side contracts. Deliberately schema-flexible: no fixed columns,
since the real organization/employee data sources don't exist yet."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class OrganizationProfile(BaseModel):
    """Structural/strategic metadata about an organization. Everything beyond
    the identifier is an open bag so new attribute types never require a
    contract change."""

    organization_id: str
    name: str | None = None
    core_attributes: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AttributeField(BaseModel):
    """Describes one employee attribute that *may* exist for an organization —
    never the attribute's actual values. Row-level data stays out of the
    Hypothesis Agent entirely."""

    name: str
    category: str = "other"
    data_type: str = "unknown"
    coverage_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    description: str | None = None


class EmployeeDataLandscape(BaseModel):
    """A schema-level summary of what employee data *could* be available for
    an organization, used to judge feasibility without ever touching raw
    employee records."""

    organization_id: str
    employee_count_estimate: int | None = None
    available_fields: list[AttributeField] = Field(default_factory=list)
    notes: str | None = None

    def categories(self) -> set[str]:
        return {f.category for f in self.available_fields}


class OrganizationUnderstanding(BaseModel):
    """Synthesized narrative produced by the pluggable UnderstandingEngine —
    the input every downstream reasoning node conditions on."""

    organization_id: str
    narrative: str
    key_tensions: list[str] = Field(default_factory=list)
    strategic_priorities: list[str] = Field(default_factory=list)
    notable_data_signals: list[str] = Field(default_factory=list)
    engine_used: str = "unknown"
