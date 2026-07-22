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
            understanding=state["organization_understanding"], similar_prior=similar_prior
        )
        result = await critic_chain.run(candidate, context)

        # Deterministic dedup guard: don't rely on the LLM to notice a
        # near-duplicate. Anything above the similarity threshold is flagged
        # regardless of what the critic said, and unconditionally discarded
        # later (plugins/search_heuristics/entropy_heuristic.py) — this is
        # what guarantees a saved hypothesis is never already in the store.
        if candidate.embedding is not None:
            max_similarity = max(
                (
                    EmbeddingService.cosine_similarity(candidate.embedding, prior.embedding)
                    for prior in similar_prior
                    if prior.embedding is not None
                ),
                default=0.0,
            )
            if max_similarity >= duplicate_threshold:
                result = result.model_copy(
                    update={
                        "similar_to_prior": True,
                        "issues": result.issues
                        + [
                            f"Near-duplicate of an existing stored hypothesis "
                            f"(cosine similarity {max_similarity:.3f} >= {duplicate_threshold})."
                        ],
                    }
                )

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
