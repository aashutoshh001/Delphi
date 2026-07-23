"""Investigation Planner contracts — see docs/PLATFORM_ARCHITECTURE.md §7."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field

from insight_pipeline.contracts.organization_knowledge import OrganizationKnowledge


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class VariableSpec(BaseModel):
    name: str
    role: Literal["independent", "dependent", "moderator", "mediator", "control"]
    expected_type: Literal["numeric", "categorical", "ordinal", "boolean", "text", "datetime"]
    data_category: str = "other"


class PopulationSpec(BaseModel):
    description: str
    inclusion_criteria: list[str] = Field(default_factory=list)
    exclusion_criteria: list[str] = Field(default_factory=list)


class InvestigationPlan(BaseModel):
    """Output of the Investigation Planner Agent. Never touches data — this
    is purely "what would be needed to validate this hypothesis?"."""

    id: str = Field(default_factory=lambda: _new_id("plan"))
    hypothesis_package_id: str
    organization_id: str
    variables_required: list[VariableSpec] = Field(default_factory=list)
    target_population: PopulationSpec
    segmentation_strategy: list[str] = Field(default_factory=list)
    potential_confounders: list[str] = Field(default_factory=list)
    filtering_rules: list[str] = Field(default_factory=list)
    statistical_questions: list[str] = Field(default_factory=list)
    business_questions: list[str] = Field(default_factory=list)
    validation_strategy: str = ""
    recommended_analysis_types: list[str] = Field(default_factory=list)
    potential_risks: list[str] = Field(default_factory=list)
    suggested_visualizations: list[str] = Field(default_factory=list)
    relevant_knowledge: list[OrganizationKnowledge] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)
