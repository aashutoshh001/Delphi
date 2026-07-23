"""Narrative Agent contracts — see docs/PLATFORM_ARCHITECTURE.md §12."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class Narrative(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("narrative"))
    executive_summary: str = ""
    storyline: list[str] = Field(default_factory=list)
    key_messages: list[str] = Field(default_factory=list)
    business_narrative: str = ""
    supporting_evidence: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    future_questions: list[str] = Field(default_factory=list)
