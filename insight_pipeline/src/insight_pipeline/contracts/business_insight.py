"""Business Insight Agent contracts — see docs/PLATFORM_ARCHITECTURE.md §11.
Consulting synthesis, not statistical reporting."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class BusinessFinding(BaseModel):
    statement: str
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)


class BusinessRisk(BaseModel):
    description: str
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    likelihood: Literal["low", "medium", "high"] = "medium"
    affected_population: str = ""


class BusinessOpportunity(BaseModel):
    description: str
    potential_value: str = ""
    feasibility: Literal["low", "medium", "high"] = "medium"


class Recommendation(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("rec"))
    action: str
    rationale: str
    priority: int = 3
    expected_roi: str | None = None
    owner_suggestion: str | None = None


class BusinessInsights(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("insights"))
    findings: list[BusinessFinding] = Field(default_factory=list)
    risks: list[BusinessRisk] = Field(default_factory=list)
    opportunities: list[BusinessOpportunity] = Field(default_factory=list)
    financial_impact: str | None = None
    organizational_impact: str = ""
    employee_impact: str = ""
    strategic_recommendations: list[Recommendation] = Field(default_factory=list)
    priority_ranking: list[str] = Field(default_factory=list)
