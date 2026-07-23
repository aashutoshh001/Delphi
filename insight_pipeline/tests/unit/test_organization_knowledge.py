from hypothesis_agent.adapters.embeddings.hash_embedding_service import HashEmbeddingService
from insight_pipeline.adapters.organization_knowledge.embedding_retriever import (
    EmbeddingOrganizationKnowledgeRetriever,
)
from insight_pipeline.adapters.organization_knowledge.in_memory_repository import (
    InMemoryOrganizationKnowledgeRepository,
)
from insight_pipeline.contracts.organization_knowledge import OrganizationKnowledgeDocument


async def test_empty_repository_returns_no_knowledge():
    repo = InMemoryOrganizationKnowledgeRepository()
    retriever = EmbeddingOrganizationKnowledgeRetriever(repo, HashEmbeddingService())
    result = await retriever.retrieve("promotion policy", "org-1")
    assert result == []


async def test_retrieve_ranks_relevant_document_first():
    repo = InMemoryOrganizationKnowledgeRepository()
    await repo.add_document(
        OrganizationKnowledgeDocument(
            organization_id="org-1",
            category="promotion_policy",
            title="Promotion Policy",
            content="Internal mobility and promotion are based on demonstrated leadership competency.",
        )
    )
    await repo.add_document(
        OrganizationKnowledgeDocument(
            organization_id="org-1",
            category="culture_handbook",
            title="Office Snack Policy",
            content="Snacks are restocked every Tuesday in the break room.",
        )
    )
    retriever = EmbeddingOrganizationKnowledgeRetriever(repo, HashEmbeddingService())
    result = await retriever.retrieve("promotion and leadership competency", "org-1", top_k=1)
    assert len(result) == 1
    assert result[0].category == "promotion_policy"


async def test_retrieve_filters_by_organization():
    repo = InMemoryOrganizationKnowledgeRepository()
    await repo.add_document(
        OrganizationKnowledgeDocument(organization_id="org-1", title="A", content="mobility policy text")
    )
    retriever = EmbeddingOrganizationKnowledgeRetriever(repo, HashEmbeddingService())
    result = await retriever.retrieve("mobility policy", "org-2")
    assert result == []


async def test_list_documents_filters_by_category():
    repo = InMemoryOrganizationKnowledgeRepository()
    await repo.add_document(
        OrganizationKnowledgeDocument(organization_id="org-1", category="mission", title="M", content="...")
    )
    await repo.add_document(
        OrganizationKnowledgeDocument(organization_id="org-1", category="vision", title="V", content="...")
    )
    docs = await repo.list_documents("org-1", category="mission")
    assert len(docs) == 1
    assert docs[0].title == "M"
