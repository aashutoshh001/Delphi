from abc import ABC, abstractmethod

from insight_pipeline.contracts.insight_package import InsightPackage


class InsightPackageRepository(ABC):
    """Persistence for the final report package. JSON-file-backed today
    (mirrors JsonHypothesisStore), a real DB later with no interface change."""

    @abstractmethod
    async def save(self, package: InsightPackage) -> None: ...

    @abstractmethod
    async def get(self, package_id: str) -> InsightPackage | None: ...

    @abstractmethod
    async def list_recent(self, limit: int = 20) -> list[InsightPackage]: ...
