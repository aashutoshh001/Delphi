from abc import ABC, abstractmethod

from insight_pipeline.contracts.business_insight import BusinessInsights
from insight_pipeline.contracts.narrative import Narrative
from insight_pipeline.contracts.root_cause import RootCauseGraph


class NarrativeStrategyPlugin(ABC):
    """One narrative framing (risk-led, opportunity-led, balanced, ...)."""

    strategy_name: str

    @abstractmethod
    async def narrate(
        self, insights: BusinessInsights, root_cause: RootCauseGraph
    ) -> Narrative: ...
