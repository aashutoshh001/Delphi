"""The Hypothesis Agent's entire public interface. Downstream code — a
future orchestrator, an HTTP handler, a CLI, a test — only ever needs this
module and `contracts.HypothesisPackage`."""

from __future__ import annotations

import uuid

from hypothesis_agent.config.settings import AgentConfig
from hypothesis_agent.contracts.hypothesis import HypothesisPackage
from hypothesis_agent.contracts.memory import FeedbackSummary, HistoricalHypothesisRecord
from hypothesis_agent.di.container import build_dependencies
from hypothesis_agent.logging_setup import configure_logging, get_logger
from hypothesis_agent.reasoning.dependencies import AgentDependencies
from hypothesis_agent.reasoning.graph import build_hypothesis_graph
from hypothesis_agent.reasoning.state import new_initial_state

logger = get_logger("agent")


class HypothesisAgent:
    def __init__(self, dependencies: AgentDependencies) -> None:
        self._deps = dependencies
        configure_logging(dependencies.config.logging)

    @classmethod
    def from_config(cls, config_path: str | None = None) -> "HypothesisAgent":
        config = AgentConfig.load(config_path)
        return cls(build_dependencies(config))

    @property
    def dependencies(self) -> AgentDependencies:
        return self._deps

    async def discover(self, organization_id: str) -> HypothesisPackage:
        """Runs the full search loop and returns exactly one Structured
        Hypothesis Package. Also persists it to historical memory and offers
        it to the (currently no-op) downstream Analysis Agent gateway."""
        # Same shape as HistoricalHypothesisRecord's own default id (see
        # contracts/memory.py) — generated up front instead of left to that
        # model's default_factory so every LLM call made *during* this run
        # can already be tagged with the id the record ends up saved under,
        # grouping the whole run into one Langfuse session (see
        # reasoning/observability.py). A caller that later POSTs this
        # hypothesis to the Investigation Pipeline tagged with this same id
        # (the frontend already does, for an unrelated reason — see
        # script.js's requestInvestigation) gets that run folded into the
        # same session too, for free.
        session_id = f"hist_{uuid.uuid4().hex[:12]}"
        graph = build_hypothesis_graph(self._deps)
        initial_state = new_initial_state(
            organization_id=organization_id,
            max_iterations=self._deps.config.search.max_iterations,
            session_id=session_id,
        )
        logger.info("starting hypothesis discovery", extra={"extra_fields": {"organization_id": organization_id}})

        final_state = await graph.ainvoke(initial_state, config={"recursion_limit": 200})
        package = final_state["final_package"]

        await self._deps.historical_memory_repository.save(
            HistoricalHypothesisRecord(
                id=session_id,
                organization_id=package.organization_id,
                headline=package.headline,
                summary=package.summary,
                statement=package.hypothesis_statement,
                mechanism=package.mechanism_explanation,
                lens=package.business_lens,
                target_constructs=package.target_constructs,
                embedding=await self._deps.embedding_service.embed(
                    f"{package.hypothesis_statement} {package.mechanism_explanation}"
                ),
                scorecard=package.scorecard,
                critique=package.critique,
                search_stats=package.search_stats,
                feedback_summary=FeedbackSummary(),
            )
        )
        await self._deps.analysis_agent_gateway.submit(package)

        logger.info(
            "hypothesis discovery complete",
            extra={"extra_fields": {"lens": package.business_lens, "composite": package.scorecard.composite}},
        )
        return package
