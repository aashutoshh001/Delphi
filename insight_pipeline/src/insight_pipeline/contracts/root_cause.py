"""Root Cause Discovery contracts — see docs/PLATFORM_ARCHITECTURE.md §10."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class CausalNode(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("node"))
    name: str
    node_type: Literal["driver", "mediator", "moderator", "outcome", "bottleneck"]
    description: str = ""


class CausalEdge(BaseModel):
    source: str
    target: str
    relationship_type: Literal["causes", "mediates", "moderates", "correlates_with"]
    strength: float = Field(ge=0.0, le=1.0, default=0.5)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    evidence_refs: list[str] = Field(default_factory=list)


class RootCauseGraph(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("rcg"))
    nodes: list[CausalNode] = Field(default_factory=list)
    edges: list[CausalEdge] = Field(default_factory=list)
    potential_mechanisms: list[str] = Field(default_factory=list)
    supporting_evidence: list[str] = Field(default_factory=list)
    alternative_explanations: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
