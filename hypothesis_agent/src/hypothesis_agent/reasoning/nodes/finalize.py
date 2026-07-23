from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from hypothesis_agent.contracts.hypothesis import (
    CritiqueResult,
    DownstreamHints,
    HypothesisPackage,
    InvestigationSeed,
    Provenance,
    SearchStatistics,
)
from hypothesis_agent.contracts.llm import LLMMessage, LLMRequest
from hypothesis_agent.contracts.memory import ReasoningTraceEntry
from hypothesis_agent.logging_setup import get_logger
from hypothesis_agent.reasoning.dependencies import AgentDependencies
from hypothesis_agent.reasoning.observability import session_metadata
from hypothesis_agent.reasoning.search.frontier import diversity_score
from hypothesis_agent.reasoning.state import HypothesisSearchState

logger = get_logger("nodes.finalize")


class _HeadlineResponse(BaseModel):
    headline: str
    summary: str


def _clip(text: str, limit: int) -> str:
    text = text.strip().strip('"')
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


async def _generate_headline_and_summary(
    deps: AgentDependencies, statement: str, mechanism: str, lens: str, session_id: str | None
) -> _HeadlineResponse:
    """Soft length limits, enforced in code rather than schema validation —
    an LLM-produced string that's a few characters over a hard `max_length`
    would otherwise fail Pydantic validation and lose the entire (expensive,
    already-completed) search on the very last step."""
    template = deps.prompts.get("headline_and_summary")
    rendered = template.render(lens=lens, statement=statement, mechanism=mechanism)
    request = LLMRequest(
        messages=[
            LLMMessage(role="system", content=rendered.system),
            LLMMessage(role="user", content=rendered.user),
        ],
        temperature=0.6,
        metadata=session_metadata(session_id),
    )
    result = await deps.llm_service.complete_structured(request, _HeadlineResponse)
    return _HeadlineResponse(
        headline=_clip(result.headline, 100),
        summary=_clip(result.summary, 400),
    )


async def _generate_investigation_seed(
    deps: AgentDependencies,
    narrative: str,
    statement: str,
    mechanism: str,
    lens: str,
    constructs: list[str],
    session_id: str | None,
) -> InvestigationSeed:
    template = deps.prompts.get("investigation_seed")
    rendered = template.render(
        narrative=narrative,
        lens=lens,
        statement=statement,
        mechanism=mechanism,
        constructs=", ".join(constructs),
    )
    request = LLMRequest(
        messages=[
            LLMMessage(role="system", content=rendered.system),
            LLMMessage(role="user", content=rendered.user),
        ],
        temperature=0.5,
        metadata=session_metadata(session_id),
    )
    return await deps.llm_service.complete_structured(request, InvestigationSeed)


_LENS_ANALYSIS_HINTS: dict[str, list[str]] = {
    "burnout_resilience": ["correlational analysis", "moderation analysis"],
    "skill_concentration": ["network/concentration analysis", "risk exposure analysis"],
    "promotion_equity": ["logistic regression", "fairness/disparate-impact analysis"],
    "leadership_influence": ["mediation analysis", "multilevel modeling"],
    "communication_protection": ["moderation analysis", "correlational analysis"],
    "attrition_hidden_drivers": ["survival analysis", "predictive modeling"],
    "learning_velocity": ["longitudinal trend analysis"],
    "compensation_fairness": ["equity/dispersion analysis"],
    "psychometric_fit": ["profile-outcome matching analysis"],
    "network_effects": ["organizational network analysis"],
}


def make_finalize_node(deps: AgentDependencies):
    async def finalize(state: HypothesisSearchState) -> dict[str, Any]:
        best = state["best_candidate"]
        if best is None or best.scorecard is None:
            raise RuntimeError("hypothesis search completed with no scored candidate")

        archive = state["archive"]
        stats = SearchStatistics(
            iterations_run=state["iteration"],
            candidates_generated=len(archive),
            candidates_discarded=sum(1 for c in archive if c.status == "rejected"),
            lenses_explored=sorted({c.lens for c in archive}),
            diversity_score=diversity_score(archive),
            termination_reason=state.get("termination_reason", "unknown"),
        )
        downstream_hints = DownstreamHints(
            suggested_analysis_types=_LENS_ANALYSIS_HINTS.get(best.lens, ["exploratory analysis"]),
            relevant_data_categories=sorted(state["data_landscape"].categories()),
            notes="Hints only — the Hypothesis Agent has no knowledge of downstream agent capabilities.",
        )
        headline_and_summary = await _generate_headline_and_summary(
            deps, best.statement, best.mechanism, best.lens, state.get("session_id")
        )
        investigation_seed = None
        if deps.config.search.generate_investigation_seed:
            investigation_seed = await _generate_investigation_seed(
                deps,
                state["organization_understanding"].narrative,
                best.statement,
                best.mechanism,
                best.lens,
                best.target_constructs,
                state.get("session_id"),
            )
        package = HypothesisPackage(
            organization_id=state["organization_id"],
            headline=headline_and_summary.headline,
            summary=headline_and_summary.summary,
            hypothesis_statement=best.statement,
            mechanism_explanation=best.mechanism,
            business_lens=best.lens,
            target_constructs=best.target_constructs,
            proposed_population=best.proposed_population,
            scorecard=best.scorecard,
            critique=best.critique or CritiqueResult(),
            reasoning_path=state["reasoning_trace"],
            search_stats=stats,
            downstream_hints=downstream_hints,
            investigation_seed=investigation_seed,
            provenance=Provenance(
                llm_model=deps.config.llm.model,
                embedding_model=deps.config.embedding.model,
                understanding_engine=state["organization_understanding"].engine_used,
                config_snapshot=deps.config.model_dump(),
            ),
        )

        logger.info(
            "finalized hypothesis package",
            extra={"extra_fields": {"lens": best.lens, "composite": best.composite_score()}},
        )
        trace = state["reasoning_trace"] + [
            ReasoningTraceEntry(
                step="finalize",
                iteration=state["iteration"],
                summary=f"Selected lens '{best.lens}' hypothesis, composite={best.composite_score():.3f}.",
            )
        ]
        return {"final_package": package, "reasoning_trace": trace}

    return finalize
