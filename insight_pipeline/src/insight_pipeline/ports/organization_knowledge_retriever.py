from abc import ABC, abstractmethod

from insight_pipeline.contracts.organization_knowledge import OrganizationKnowledge


class OrganizationKnowledgeRetriever(ABC):
    """Semantic search over organization knowledge. Analogous to
    HistoricalMemoryRepository.search_similar. Must behave correctly against
    an empty repository — every consumer is optional-context, not required."""

    @abstractmethod
    async def retrieve(
        self, query: str, organization_id: str, top_k: int = 5
    ) -> list[OrganizationKnowledge]: ...
