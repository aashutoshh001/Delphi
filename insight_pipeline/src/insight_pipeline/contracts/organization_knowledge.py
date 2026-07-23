"""Organization Knowledge contracts — see docs/PLATFORM_ARCHITECTURE.md §5.
Retrieved, cited chunks, never a raw document dump into a prompt."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

KNOWLEDGE_CATEGORIES: tuple[str, ...] = (
    "hr_policy",
    "promotion_policy",
    "compensation_policy",
    "competency_framework",
    "leadership_philosophy",
    "company_values",
    "culture_handbook",
    "onboarding_guide",
    "internal_documentation",
    "organizational_objectives",
    "mission",
    "vision",
    "behavioral_expectations",
)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class OrganizationKnowledgeDocument(BaseModel):
    """A stored document (or chunk of one). What `OrganizationKnowledgeRepository`
    deals in — raw storage, not relevance-ranked."""

    id: str = Field(default_factory=lambda: _new_id("doc"))
    organization_id: str
    category: str = "internal_documentation"
    title: str
    source_uri: str | None = None
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OrganizationKnowledge(BaseModel):
    """One retrieved, query-relevant chunk — what reasoning agents actually
    consume via `OrganizationKnowledgeRetriever.retrieve()`."""

    document_id: str
    category: str
    title: str
    excerpt: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    source_uri: str | None = None
