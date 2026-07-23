from abc import ABC, abstractmethod

from insight_pipeline.contracts.organization_knowledge import OrganizationKnowledgeDocument


class OrganizationKnowledgeRepository(ABC):
    """Raw storage access for policy/culture/values documents. Analogous to
    HistoricalMemoryRepository.list_recent — no relevance ranking here."""

    @abstractmethod
    async def get_document(self, document_id: str) -> OrganizationKnowledgeDocument: ...

    @abstractmethod
    async def list_documents(
        self, organization_id: str, category: str | None = None
    ) -> list[OrganizationKnowledgeDocument]: ...

    @abstractmethod
    async def add_document(self, document: OrganizationKnowledgeDocument) -> None: ...
