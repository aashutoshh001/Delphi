from abc import ABC, abstractmethod

from hypothesis_agent.contracts.organization import EmployeeDataLandscape
from insight_pipeline.contracts.dataset import RetrievalQuery
from insight_pipeline.contracts.investigation import InvestigationPlan


class QueryPlanner(ABC):
    """Maps InvestigationPlan.variables_required onto actually-available
    field names for this organization, producing a concrete RetrievalQuery."""

    @abstractmethod
    async def plan(
        self, investigation_plan: InvestigationPlan, landscape: EmployeeDataLandscape
    ) -> RetrievalQuery: ...
