from abc import ABC, abstractmethod

from hypothesis_agent.contracts.memory import HistoricalHypothesisRecord


class HistoricalMemoryRepository(ABC):
    """Store of previously generated hypotheses, used for novelty checks and
    cross-run memory. Must behave correctly against an empty store — there is
    no historical data yet."""

    @abstractmethod
    async def search_similar(
        self, embedding: list[float], organization_id: str | None, top_k: int = 5
    ) -> list[HistoricalHypothesisRecord]: ...

    @abstractmethod
    async def list_recent(
        self, organization_id: str | None, limit: int = 20
    ) -> list[HistoricalHypothesisRecord]: ...

    @abstractmethod
    async def save(self, record: HistoricalHypothesisRecord) -> None: ...
