"""Construct Grounding Agent — V2 architecture plan Part 4B. First insight
stage: maps the creative hypothesis's constructs onto real SHL Metric
Framework columns before anything else runs. Every later agent (investigation
planner, analytics, root cause, business insight, visualization) only ever
sees columns that passed through here."""

from __future__ import annotations

from hypothesis_agent.contracts.hypothesis import HypothesisPackage

from insight_pipeline.contracts.grounding import GroundingMap
from insight_pipeline.framework.registry import FrameworkRegistry
from insight_pipeline.logging_setup import get_logger
from insight_pipeline.ports.construct_grounding_engine import ConstructGroundingEngine

logger = get_logger("agents.construct_grounding")


class ConstructGroundingAgent:
    def __init__(self, engine: ConstructGroundingEngine) -> None:
        self._engine = engine

    async def run(self, hypothesis_package: HypothesisPackage, registry: FrameworkRegistry) -> GroundingMap:
        grounding_map = await self._engine.ground(hypothesis_package, registry)
        logger.info(
            "construct grounding complete",
            extra={
                "extra_fields": {
                    "hypothesis_package_id": hypothesis_package.package_id,
                    "grounded_constructs": len(grounding_map.grounded),
                    "ungrounded_constructs": len(grounding_map.ungrounded),
                    "rejected_column_names": len(grounding_map.rejected_column_names),
                }
            },
        )
        return grounding_map
