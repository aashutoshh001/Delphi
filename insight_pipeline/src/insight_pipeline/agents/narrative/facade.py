"""Narrative Agent — see docs/PLATFORM_ARCHITECTURE.md §12. Converts
multiple isolated findings into an executive story."""

from __future__ import annotations

from insight_pipeline.contracts.business_insight import BusinessInsights
from insight_pipeline.contracts.narrative import Narrative
from insight_pipeline.contracts.root_cause import RootCauseGraph
from insight_pipeline.logging_setup import get_logger
from insight_pipeline.plugins.narrative_strategies.base import NarrativeStrategyPlugin

logger = get_logger("agents.narrative")


class NarrativeAgent:
    def __init__(self, strategy: NarrativeStrategyPlugin) -> None:
        self._strategy = strategy

    async def run(
        self, insights: BusinessInsights, root_cause: RootCauseGraph, session_id: str | None = None
    ) -> Narrative:
        narrative = await self._strategy.narrate(insights, root_cause, session_id=session_id)
        logger.info(
            "narrative produced",
            extra={"extra_fields": {"key_messages": len(narrative.key_messages)}},
        )
        return narrative
