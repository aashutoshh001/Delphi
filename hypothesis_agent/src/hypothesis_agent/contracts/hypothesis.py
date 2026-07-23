"""Hypothesis-side contracts: search states, evaluation, and the final
Structured Hypothesis Package handed to downstream agents."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from hypothesis_agent.contracts.memory import ReasoningTraceEntry

EVALUATION_DIMENSIONS: tuple[str, ...] = (
    "business_value",
    "novelty",
    "depth",
    "actionability",
    "strategic_importance",
    "feasibility",
    "organizational_impact",
    "expected_insight",
    "confidence",
    "future_extensibility",
)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BusinessLens(BaseModel):
    """A named thematic direction in hypothesis space, e.g. 'burnout_resilience'.
    The unit the search heuristic diversifies over (High Entropy Requirement)."""

    id: str
    display_name: str
    description: str
    seed_questions: list[str] = Field(default_factory=list)
    relevant_construct_categories: list[str] = Field(default_factory=list)


class SearchDirective(BaseModel):
    """Output of generate_search_direction: which region of hypothesis space
    to explore next, and why."""

    id: str = Field(default_factory=lambda: _new_id("dir"))
    lens: str
    guiding_question: str
    target_constructs: list[str] = Field(default_factory=list)
    rationale: str
    parent_candidate_id: str | None = None


class DimensionScore(BaseModel):
    dimension: str
    value: float = Field(ge=0.0, le=1.0)
    rationale: str = ""
    evaluator: str = "unknown"


class EvaluationScorecard(BaseModel):
    business_value: float = Field(ge=0.0, le=1.0, default=0.0)
    novelty: float = Field(ge=0.0, le=1.0, default=0.0)
    depth: float = Field(ge=0.0, le=1.0, default=0.0)
    actionability: float = Field(ge=0.0, le=1.0, default=0.0)
    strategic_importance: float = Field(ge=0.0, le=1.0, default=0.0)
    feasibility: float = Field(ge=0.0, le=1.0, default=0.0)
    organizational_impact: float = Field(ge=0.0, le=1.0, default=0.0)
    expected_insight: float = Field(ge=0.0, le=1.0, default=0.0)
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    future_extensibility: float = Field(ge=0.0, le=1.0, default=0.0)
    composite: float = Field(ge=0.0, le=1.0, default=0.0)
    dimension_notes: dict[str, str] = Field(default_factory=dict)

    def as_dimension_map(self) -> dict[str, float]:
        return {d: getattr(self, d) for d in EVALUATION_DIMENSIONS}


class CritiqueResult(BaseModel):
    is_obvious: bool = False
    executive_relevance: str = ""
    creates_actionable_decision: bool = True
    similar_to_prior: bool = False
    similar_prior_ids: list[str] = Field(default_factory=list)
    reveals_hidden_mechanism: bool = True
    downstream_feasible: bool = True
    issues: list[str] = Field(default_factory=list)
    suggested_improvements: list[str] = Field(default_factory=list)
    critic_name: str = "unknown"


class HypothesisCandidate(BaseModel):
    """One node in the hypothesis search tree."""

    id: str = Field(default_factory=lambda: _new_id("cand"))
    iteration: int = 0
    parent_id: str | None = None
    lens: str
    statement: str
    mechanism: str = ""
    target_constructs: list[str] = Field(default_factory=list)
    proposed_population: str | None = None
    embedding: list[float] | None = None
    reasoning_trace: list[str] = Field(default_factory=list)
    scorecard: EvaluationScorecard | None = None
    critique: CritiqueResult | None = None
    status: Literal[
        "proposed", "critiqued", "scored", "improved", "rejected", "finalist"
    ] = "proposed"

    def composite_score(self) -> float:
        return self.scorecard.composite if self.scorecard else 0.0


class SearchStatistics(BaseModel):
    iterations_run: int = 0
    candidates_generated: int = 0
    candidates_discarded: int = 0
    lenses_explored: list[str] = Field(default_factory=list)
    diversity_score: float = 0.0
    termination_reason: str = "unknown"


class DownstreamHints(BaseModel):
    """Non-binding hints for whichever downstream agents eventually exist.
    The Hypothesis Agent has no knowledge of how they work, so these are
    suggestions only, never a contract it enforces."""

    suggested_analysis_types: list[str] = Field(default_factory=list)
    relevant_data_categories: list[str] = Field(default_factory=list)
    notes: str = ""


class Provenance(BaseModel):
    agent_version: str = "0.1.0"
    llm_model: str | None = None
    embedding_model: str | None = None
    understanding_engine: str | None = None
    generated_by: str = "hypothesis_agent"
    config_snapshot: dict = Field(default_factory=dict)


class InvestigationSeed(BaseModel):
    """Forward-looking hints for the (separate, optional) downstream
    Investigation Pipeline — see Delphi/docs/PLATFORM_ARCHITECTURE.md §6.
    Entirely optional and non-authoritative: a future Investigation Planner
    Agent re-derives its own plan and may agree, extend, or ignore these.
    Populated only when `search.generate_investigation_seed` is enabled —
    off by default so a Hypothesis Agent used standalone never pays for an
    LLM call whose only consumer is a pipeline it may not even have
    installed."""

    expected_investigation_objectives: list[str] = Field(default_factory=list)
    potential_organizational_risks: list[str] = Field(default_factory=list)
    potential_organizational_opportunities: list[str] = Field(default_factory=list)
    suggested_organizational_questions: list[str] = Field(default_factory=list)
    suggested_statistical_analyses: list[str] = Field(default_factory=list)
    suggested_visualization_themes: list[str] = Field(default_factory=list)
    relevant_organizational_policies: list[str] = Field(default_factory=list)
    relevant_organizational_constructs: list[str] = Field(default_factory=list)
    business_context: str = ""


class HypothesisPackage(BaseModel):
    """The Structured Hypothesis Package — the entire interface between the
    Hypothesis Agent and every downstream agent."""

    package_id: str = Field(default_factory=lambda: _new_id("pkg"))
    organization_id: str
    generated_at: datetime = Field(default_factory=_utcnow)
    headline: str = ""
    summary: str = ""
    hypothesis_statement: str
    mechanism_explanation: str
    business_lens: str
    target_constructs: list[str] = Field(default_factory=list)
    proposed_population: str | None = None
    scorecard: EvaluationScorecard
    critique: CritiqueResult
    reasoning_path: list["ReasoningTraceEntry"] = Field(default_factory=list)
    search_stats: SearchStatistics
    downstream_hints: DownstreamHints = Field(default_factory=DownstreamHints)
    investigation_seed: InvestigationSeed | None = None
    provenance: Provenance = Field(default_factory=Provenance)
