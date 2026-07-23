from __future__ import annotations

from hypothesis_agent.ports.embedding_service import EmbeddingService
from insight_pipeline.contracts.organization_knowledge import OrganizationKnowledge
from insight_pipeline.ports.organization_knowledge_repository import (
    OrganizationKnowledgeRepository,
)
from insight_pipeline.ports.organization_knowledge_retriever import (
    OrganizationKnowledgeRetriever,
)


class EmbeddingOrganizationKnowledgeRetriever(OrganizationKnowledgeRetriever):
    """Embeds every document on the fly and ranks by cosine similarity —
    same no-cache-needed pattern as JsonHypothesisStore.search_similar, fine
    at the scale of a policy/culture document set. Reuses
    hypothesis_agent's EmbeddingService port rather than redefining one."""

    def __init__(
        self, repository: OrganizationKnowledgeRepository, embedding_service: EmbeddingService
    ) -> None:
        self._repository = repository
        self._embedding_service = embedding_service

    async def retrieve(
        self, query: str, organization_id: str, top_k: int = 5
    ) -> list[OrganizationKnowledge]:
        documents = await self._repository.list_documents(organization_id)
        if not documents:
            return []
        query_embedding = await self._embedding_service.embed(query)
        scored: list[tuple[float, OrganizationKnowledge]] = []
        for document in documents:
            doc_embedding = await self._embedding_service.embed(f"{document.title} {document.content}")
            similarity = EmbeddingService.cosine_similarity(query_embedding, doc_embedding)
            scored.append(
                (
                    similarity,
                    OrganizationKnowledge(
                        document_id=document.id,
                        category=document.category,
                        title=document.title,
                        excerpt=document.content[:500],
                        relevance_score=max(0.0, min(1.0, similarity)),
                        source_uri=document.source_uri,
                    ),
                )
            )
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [knowledge for _similarity, knowledge in scored[:top_k]]
