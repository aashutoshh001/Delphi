from abc import ABC, abstractmethod

from insight_pipeline.contracts.dataset import RetrievedDataset
from insight_pipeline.contracts.investigation import InvestigationPlan


class DatasetRetriever(ABC):
    """Orchestrates QueryPlanner + EmployeeDataRepository into one
    RetrievedDataset. The Data Retrieval Agent's only real dependency."""

    @abstractmethod
    async def retrieve(self, investigation_plan: InvestigationPlan) -> RetrievedDataset: ...
