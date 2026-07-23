"""LangGraph state for the hypothesis search loop. A TypedDict so LangGraph
can apply partial-key updates per node; every value is a `contracts/` model
or a primitive, never an untyped dict."""

from __future__ import annotations

from typing import TypedDict

from hypothesis_agent.contracts.hypothesis import (
    DimensionScore,
    HypothesisCandidate,
    HypothesisPackage,
    SearchDirective,
)
from hypothesis_agent.contracts.memory import ReasoningTraceEntry
from hypothesis_agent.contracts.organization import (
    EmployeeDataLandscape,
    OrganizationProfile,
    OrganizationUnderstanding,
)


class HypothesisSearchState(TypedDict, total=False):
    organization_id: str
    max_iterations: int
    # Groups every LLM call this search run makes into one Langfuse session
    # (see reasoning/observability.py). None when Langfuse isn't configured
    # or the caller didn't ask for one — every node treats it as optional.
    session_id: str | None

    organization_profile: OrganizationProfile
    data_landscape: EmployeeDataLandscape
    organization_understanding: OrganizationUnderstanding
    lens_priors: dict[str, float]

    iteration: int
    current_directive: SearchDirective
    current_candidate: HypothesisCandidate
    partial_scores: dict[str, DimensionScore]

    frontier: list[HypothesisCandidate]
    archive: list[HypothesisCandidate]
    best_candidate: HypothesisCandidate | None

    reasoning_trace: list[ReasoningTraceEntry]
    termination_reason: str
    final_package: HypothesisPackage


def new_initial_state(
    organization_id: str, max_iterations: int, session_id: str | None = None
) -> HypothesisSearchState:
    return HypothesisSearchState(
        organization_id=organization_id,
        max_iterations=max_iterations,
        session_id=session_id,
        iteration=0,
        frontier=[],
        archive=[],
        best_candidate=None,
        reasoning_trace=[],
        lens_priors={},
    )
