"""Deterministic QueryPlanner — B3 in the V2 architecture plan (Part 4½.1):
zero LLM calls. `InvestigationPlan.variables_required` is already
constrained to real, grounded column names by the time it reaches here (see
the Construct Grounding Agent + the reworked Investigation Planner), so
"map variables onto actually-available field names" is just a verbatim
passthrough — the LLM-based query-mismatch failure mode (invented variable
names that never match anything) is structurally eliminated one stage
earlier, not papered over here.

Still double-checks each variable against the landscape's own field list as
defense in depth (the two sources — grounding's FrameworkRegistry and
hypothesis_agent's EmployeeDataLandscape — are built independently, so a
mismatch here would indicate a real bug worth surfacing, not something to
silently paper over)."""

from __future__ import annotations

from hypothesis_agent.contracts.organization import EmployeeDataLandscape
from insight_pipeline.contracts.dataset import RetrievalQuery
from insight_pipeline.contracts.investigation import InvestigationPlan
from insight_pipeline.logging_setup import get_logger
from insight_pipeline.ports.query_planner import QueryPlanner

logger = get_logger("adapters.query_planning.grounded")


class GroundedQueryPlanner(QueryPlanner):
    engine_name = "grounded"

    async def plan(
        self, investigation_plan: InvestigationPlan, landscape: EmployeeDataLandscape
    ) -> RetrievalQuery:
        known_fields = {f.name for f in landscape.available_fields}
        requested = [v.name for v in investigation_plan.variables_required]
        mismatched = [name for name in requested if name not in known_fields]
        if mismatched:
            logger.warning(
                "grounded variable(s) not found in the employee data landscape — "
                "grounding and landscape may be out of sync",
                extra={"extra_fields": {"mismatched": mismatched}},
            )
        return RetrievalQuery(
            organization_id=investigation_plan.organization_id,
            requested_fields=[name for name in requested if name in known_fields],
            filters=investigation_plan.filtering_rules,
            segmentation=investigation_plan.segmentation_strategy,
            notes="Fields passed through verbatim from the already-grounded investigation plan (no LLM call).",
        )
