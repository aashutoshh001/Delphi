from __future__ import annotations

from pydantic import BaseModel, Field

from hypothesis_agent.contracts.llm import LLMMessage, LLMRequest
from hypothesis_agent.contracts.organization import EmployeeDataLandscape
from hypothesis_agent.ports.llm_service import LLMService
from insight_pipeline.contracts.dataset import RetrievalQuery
from insight_pipeline.contracts.investigation import InvestigationPlan
from insight_pipeline.ports.query_planner import QueryPlanner
from insight_pipeline.prompts.registry import PromptRegistry


class QueryPlanResponse(BaseModel):
    requested_fields: list[str] = Field(default_factory=list)
    filters: list[str] = Field(default_factory=list)
    segmentation: list[str] = Field(default_factory=list)
    notes: str = ""


def render_variables(plan: InvestigationPlan) -> str:
    return "\n".join(
        f"- {v.name} ({v.role}, {v.expected_type}, category={v.data_category})"
        for v in plan.variables_required
    ) or "(none specified)"


def render_fields(landscape: EmployeeDataLandscape) -> str:
    return "\n".join(
        f"- {f.name}: {f.category}, {f.data_type}, coverage={f.coverage_ratio}"
        for f in landscape.available_fields
    ) or "(no known fields)"


class DirectLLMQueryPlanner(QueryPlanner):
    """Default: one structured LLM call mapping InvestigationPlan variables
    onto actually-available field names."""

    def __init__(self, llm_service: LLMService, prompts: PromptRegistry) -> None:
        self._llm = llm_service
        self._prompts = prompts

    async def plan(
        self, investigation_plan: InvestigationPlan, landscape: EmployeeDataLandscape
    ) -> RetrievalQuery:
        template = self._prompts.get("query_plan")
        rendered = template.render(
            variables=render_variables(investigation_plan),
            filtering_rules="\n".join(f"- {r}" for r in investigation_plan.filtering_rules) or "(none)",
            segmentation_strategy="\n".join(f"- {s}" for s in investigation_plan.segmentation_strategy)
            or "(none)",
            available_fields=render_fields(landscape),
        )
        request = LLMRequest(
            messages=[
                LLMMessage(role="system", content=rendered.system),
                LLMMessage(role="user", content=rendered.user),
            ],
            temperature=0.2,
            metadata={"session_id": investigation_plan.hypothesis_package_id}
            if investigation_plan.hypothesis_package_id
            else {},
        )
        result = await self._llm.complete_structured(request, QueryPlanResponse)
        known_fields = {f.name for f in landscape.available_fields}
        requested = [f for f in result.requested_fields if f in known_fields]
        return RetrievalQuery(
            organization_id=investigation_plan.organization_id,
            requested_fields=requested,
            filters=result.filters,
            segmentation=result.segmentation,
            notes=result.notes,
        )
