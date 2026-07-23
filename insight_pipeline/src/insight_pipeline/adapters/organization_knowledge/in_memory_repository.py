from __future__ import annotations

from insight_pipeline.contracts.organization_knowledge import OrganizationKnowledgeDocument
from insight_pipeline.ports.organization_knowledge_repository import (
    OrganizationKnowledgeRepository,
)


class InMemoryOrganizationKnowledgeRepository(OrganizationKnowledgeRepository):
    """Fixture-backed store. Correct against an empty repository — every
    consumer treats organization knowledge as optional context."""

    def __init__(self, documents: dict[str, OrganizationKnowledgeDocument] | None = None) -> None:
        self._documents: dict[str, OrganizationKnowledgeDocument] = dict(documents or {})

    async def get_document(self, document_id: str) -> OrganizationKnowledgeDocument:
        try:
            return self._documents[document_id]
        except KeyError as exc:
            raise KeyError(f"no organization knowledge document '{document_id}'") from exc

    async def list_documents(
        self, organization_id: str, category: str | None = None
    ) -> list[OrganizationKnowledgeDocument]:
        return [
            d
            for d in self._documents.values()
            if d.organization_id == organization_id and (category is None or d.category == category)
        ]

    async def add_document(self, document: OrganizationKnowledgeDocument) -> None:
        self._documents[document.id] = document
