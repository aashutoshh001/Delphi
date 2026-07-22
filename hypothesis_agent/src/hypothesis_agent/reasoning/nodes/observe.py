from __future__ import annotations

from typing import Any

from hypothesis_agent.contracts.memory import ReasoningTraceEntry
from hypothesis_agent.logging_setup import get_logger
from hypothesis_agent.reasoning.dependencies import AgentDependencies
from hypothesis_agent.reasoning.state import HypothesisSearchState

logger = get_logger("nodes.observe")


def make_observe_node(deps: AgentDependencies):
    async def observe(state: HypothesisSearchState) -> dict[str, Any]:
        org_id = state["organization_id"]
        profile = await deps.organization_repository.get_profile(org_id)
        landscape = await deps.employee_repository.get_data_landscape(org_id)
        counts = await deps.feedback_repository.get_lens_feedback_counts(org_id)
        lens_priors = deps.plugins.memory_policy.compute_lens_priors(counts)

        logger.info("observed organization", extra={"extra_fields": {"organization_id": org_id}})

        trace = state["reasoning_trace"] + [
            ReasoningTraceEntry(
                step="observe",
                iteration=0,
                summary=f"Fetched profile and data landscape for '{org_id}'; "
                f"{len(counts)} lens(es) have prior feedback.",
            )
        ]
        return {
            "organization_profile": profile,
            "data_landscape": landscape,
            "lens_priors": lens_priors,
            "reasoning_trace": trace,
        }

    return observe
