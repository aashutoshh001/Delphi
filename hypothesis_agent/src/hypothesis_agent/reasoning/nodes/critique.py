from __future__ import annotations

from typing import Any

from hypothesis_agent.contracts.memory import ReasoningTraceEntry
from hypothesis_agent.logging_setup import get_logger
from hypothesis_agent.plugins.critics.base import CriticChain, CriticContext
from hypothesis_agent.ports.embedding_service import EmbeddingService
from hypothesis_agent.reasoning.dependencies import AgentDependencies
from hypothesis_agent.reasoning.state import HypothesisSearchState

logger = get_logger("nodes.critique")


def make_critique_node(deps: AgentDependencies):
    critic_chain = CriticChain(deps.plugins.critics)
    duplicate_threshold = deps.config.search.duplicate_similarity_threshold

    async def critique(state: HypothesisSearchState) -> dict[str, Any]:
        candidate = state["current_candidate"]
        similar_prior = []
        if candidate.embedding is not None:
            similar_prior = await deps.historical_memory_repository.search_similar(
                candidate.embedding, state["organization_id"], top_k=3
            )

        context = CriticContext(
            understanding=state["organization_understanding"],
            similar_prior=similar_prior,
            session_id=state.get("session_id"),
        )
        result = await critic_chain.run(candidate, context)

        # Deterministic dedup guard: don't rely on the LLM to notice a
        # near-duplicate. `similar_to_prior` is fully OVERWRITTEN by the
        # cosine-similarity check whenever an embedding is available — not
        # just forced True above the threshold, but also forced False below
        # it — so the critic's own (often overcautious) opinion can never by
        # itself discard a candidate, nor let a real near-duplicate through.
        # This is what guarantees a saved hypothesis is never already in the
        # store, without also silently blocking healthy, distinct ones.
        if candidate.embedding is not None:
            max_similarity = max(
                (
                    EmbeddingService.cosine_similarity(candidate.embedding, prior.embedding)
                    for prior in similar_prior
                    if prior.embedding is not None
                ),
                default=0.0,
            )
            is_duplicate = max_similarity >= duplicate_threshold
            issues = result.issues
            if is_duplicate:
                issues = issues + [
                    f"Near-duplicate of an existing stored hypothesis "
                    f"(cosine similarity {max_similarity:.3f} >= {duplicate_threshold})."
                ]
            result = result.model_copy(update={"similar_to_prior": is_duplicate, "issues": issues})

        candidate = candidate.model_copy(update={"critique": result, "status": "critiqued"})

        logger.info(
            "critiqued candidate",
            extra={"extra_fields": {"is_obvious": result.is_obvious, "similar": result.similar_to_prior}},
        )
        trace = state["reasoning_trace"] + [
            ReasoningTraceEntry(
                step="critique",
                iteration=state["iteration"],
                summary=f"issues={len(result.issues)} obvious={result.is_obvious} similar={result.similar_to_prior}",
            )
        ]
        return {"current_candidate": candidate, "reasoning_trace": trace}

    return critique
