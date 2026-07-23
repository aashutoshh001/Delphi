from abc import ABC, abstractmethod

from insight_pipeline.contracts.dataset import DatasetHandle, RetrievalQuery


class EmployeeDataRepository(ABC):
    """The "today Excel, tomorrow SQL/Snowflake/HRIS" swappable data source.

    Deliberately distinct from `hypothesis_agent.ports.EmployeeRepository`:
    that port only ever returns a schema-level landscape (no row access,
    used pre-hypothesis). This port resolves actual scoped data, and is only
    ever called once a specific `InvestigationPlan` has authorized exactly
    what's needed — principle of least privilege applied to the pipeline."""

    @abstractmethod
    async def resolve(self, query: RetrievalQuery) -> DatasetHandle: ...
