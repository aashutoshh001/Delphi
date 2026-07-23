"""Construct Grounding contracts — V2 architecture plan Part 4B. The single
new contract that makes metric invention structurally impossible downstream:
every stage after grounding may only reference `GroundedConstruct.columns`
(or the framework's outcome/assessment columns directly), never a name the
hypothesis's own free-text `target_constructs` happened to use."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class GroundedConstruct(BaseModel):
    """One hypothesis construct, mapped to real columns. `columns` is
    guaranteed (by ConstructGroundingAgent, not by convention) to contain
    only names present in the FrameworkRegistry it was built against."""

    construct_name: str
    columns: list[str] = Field(default_factory=list)
    role: Literal["independent", "dependent", "moderator", "mediator", "control", "context"] = "context"
    rationale: str = ""


class UngroundedConstruct(BaseModel):
    """A construct with no real-column proxy — reported honestly instead of
    silently fabricated (this is what replaces the old comp_opacity-style
    invention)."""

    construct_name: str
    reason: str = ""


class GroundingMap(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("grounding"))
    hypothesis_package_id: str
    grounded: list[GroundedConstruct] = Field(default_factory=list)
    ungrounded: list[UngroundedConstruct] = Field(default_factory=list)
    outcome_columns_available: list[str] = Field(default_factory=list)
    rejected_column_names: list[str] = Field(
        default_factory=list,
        description="Names the LLM proposed that did not exist in the framework registry — "
        "kept for audit/debugging, never used downstream.",
    )
    provenance: dict[str, str] = Field(default_factory=dict)

    def all_grounded_columns(self) -> list[str]:
        seen: list[str] = []
        for construct in self.grounded:
            for column in construct.columns:
                if column not in seen:
                    seen.append(column)
        return seen

    def independent_columns(self) -> list[str]:
        return [c for g in self.grounded if g.role == "independent" for c in g.columns]

    def dependent_columns(self) -> list[str]:
        return [c for g in self.grounded if g.role == "dependent" for c in g.columns]
