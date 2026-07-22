from __future__ import annotations

from typing import Any

from hypothesis_agent.contracts.memory import ReasoningTraceEntry
from hypothesis_agent.logging_setup import get_logger
from hypothesis_agent.reasoning.dependencies import AgentDependencies
from hypothesis_agent.reasoning.state import HypothesisSearchState

logger = get_logger("nodes.understand_organization")


def make_understand_organization_node(deps: AgentDependencies):
    async def understand_organization(state: HypothesisSearchState) -> dict[str, Any]:
        understanding = await deps.understanding_engine.understand(
            state["organization_profile"], state["data_landscape"]
        )
        logger.info(
            "synthesized organization understanding",
            extra={"extra_fields": {"engine": understanding.engine_used}},
        )
        trace = state["reasoning_trace"] + [
            ReasoningTraceEntry(
                step="understand_organization",
                iteration=0,
                summary=f"Synthesized organizational narrative via '{understanding.engine_used}' engine.",
            )
        ]
        return {"organization_understanding": understanding, "reasoning_trace": trace}

    return understand_organization
