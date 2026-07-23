from __future__ import annotations

from hypothesis_agent.ports.employee_repository import EmployeeRepository
from insight_pipeline.contracts.dataset import DatasetMetadata, RetrievedDataset
from insight_pipeline.contracts.investigation import InvestigationPlan
from insight_pipeline.ports.dataset_retriever import DatasetRetriever
from insight_pipeline.ports.employee_data_repository import EmployeeDataRepository
from insight_pipeline.ports.query_planner import QueryPlanner


class DefaultDatasetRetriever(DatasetRetriever):
    """Orchestrates: fetch the landscape (what fields exist, reusing
    hypothesis_agent's own EmployeeRepository) -> plan a query against it
    -> resolve actual scoped data. No statistical reasoning happens here."""

    def __init__(
        self,
        employee_repository: EmployeeRepository,
        query_planner: QueryPlanner,
        employee_data_repository: EmployeeDataRepository,
    ) -> None:
        self._employee_repository = employee_repository
        self._query_planner = query_planner
        self._employee_data_repository = employee_data_repository

    async def retrieve(self, investigation_plan: InvestigationPlan) -> RetrievedDataset:
        landscape = await self._employee_repository.get_data_landscape(
            investigation_plan.organization_id
        )
        query = await self._query_planner.plan(investigation_plan, landscape)
        handle = await self._employee_data_repository.resolve(query)

        # Reflect what the handle *actually* resolved to (handle.columns),
        # not just what was requested — a repository may fall back to a
        # wider table (e.g. no field matched), and metadata should describe
        # reality so the Analytics Agent can still find applicable methods.
        resolved_columns = set(handle.columns)
        metadata = DatasetMetadata(
            fields=[f for f in landscape.available_fields if f.name in resolved_columns],
            population_description=investigation_plan.target_population.description,
            coverage_notes=query.notes,
        )
        return RetrievedDataset(
            investigation_plan_id=investigation_plan.id,
            handle=handle,
            metadata=metadata,
            retrieval_query_summary=(
                f"{len(query.requested_fields)} fields, "
                f"{len(query.filters)} filter(s), {len(query.segmentation)} segmentation rule(s)"
            ),
        )
