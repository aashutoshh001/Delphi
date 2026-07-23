"""QueryPlanner backed by the Strands SDK — see
docs/PLATFORM_ARCHITECTURE.md §8/§17: Data Retrieval is fundamentally "call
the right tool(s) to fetch the right thing," which fits Strands' tool-
calling agent loop better than a heavyweight planning framework. Today there
is one data-source tool (the Excel-backed landscape); as SQL/Snowflake/HRIS
adapters are added, each becomes another tool this same agent can call to
check field availability before committing to a query plan."""

from __future__ import annotations

from typing import Any

from hypothesis_agent.contracts.organization import EmployeeDataLandscape
from insight_pipeline.adapters.query_planning.direct_llm_planner import (
    QueryPlanResponse,
    render_fields,
    render_variables,
)
from insight_pipeline.contracts.dataset import RetrievalQuery
from insight_pipeline.contracts.investigation import InvestigationPlan
from insight_pipeline.ports.query_planner import QueryPlanner


class StrandsQueryPlanner(QueryPlanner):
    def __init__(self, model: Any | None = None) -> None:
        try:
            from strands import Agent
        except ImportError as exc:
            raise ImportError(
                "StrandsQueryPlanner requires the 'strands-agents' package: "
                "install insight_pipeline[strands]"
            ) from exc
        self._agent = Agent(model=model) if model is not None else Agent()

    async def plan(
        self, investigation_plan: InvestigationPlan, landscape: EmployeeDataLandscape
    ) -> RetrievalQuery:
        prompt = (
            "Map this investigation's required variables onto the actual "
            "available field names below. Only ever propose field names that "
            "literally appear in the available fields list.\n\n"
            f"Variables needed:\n{render_variables(investigation_plan)}\n\n"
            f"Filtering rules: {investigation_plan.filtering_rules}\n"
            f"Segmentation strategy: {investigation_plan.segmentation_strategy}\n\n"
            f"Available fields:\n{render_fields(landscape)}\n\n"
            "Return requested_fields (verbatim field names), filters "
            "(plain-English), segmentation (plain-English), and notes on any "
            "variable with no good match."
        )
        result = await self._agent.structured_output_async(QueryPlanResponse, prompt)
        known_fields = {f.name for f in landscape.available_fields}
        requested = [f for f in result.requested_fields if f in known_fields]
        return RetrievalQuery(
            organization_id=investigation_plan.organization_id,
            requested_fields=requested,
            filters=result.filters,
            segmentation=result.segmentation,
            notes=result.notes,
        )
