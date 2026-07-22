from __future__ import annotations

from hypothesis_agent.contracts.memory import HistoricalHypothesisRecord
from hypothesis_agent.ports.embedding_service import EmbeddingService
from hypothesis_agent.ports.historical_memory_repository import (
    HistoricalMemoryRepository,
)


class InMemoryHistoricalMemoryRepository(HistoricalMemoryRepository):
    """Process-local memory store. Correct but O(n) similarity scan — fine at
    the scale of a single process; a real vector store is a drop-in
    replacement behind the same port."""

    def __init__(self) -> None:
        self._records: list[HistoricalHypothesisRecord] = []

    async def search_similar(
        self, embedding: list[float], organization_id: str | None, top_k: int = 5
    ) -> list[HistoricalHypothesisRecord]:
        candidates = [
            r
            for r in self._records
            if r.embedding is not None
            and (organization_id is None or r.organization_id in (None, organization_id))
        ]
        scored = [
            (EmbeddingService.cosine_similarity(embedding, r.embedding), r) for r in candidates
        ]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [r for _, r in scored[:top_k]]

    async def list_recent(
        self, organization_id: str | None, limit: int = 20
    ) -> list[HistoricalHypothesisRecord]:
        matching = [
            r
            for r in self._records
            if organization_id is None or r.organization_id in (None, organization_id)
        ]
        matching.sort(key=lambda r: r.created_at, reverse=True)
        return matching[:limit]

    async def save(self, record: HistoricalHypothesisRecord) -> None:
        self._records.append(record)
