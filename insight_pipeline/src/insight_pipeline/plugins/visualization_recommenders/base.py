from abc import ABC, abstractmethod

from insight_pipeline.contracts.analytics import AnalyticsResult
from insight_pipeline.contracts.business_insight import BusinessInsights
from insight_pipeline.contracts.visualization import VisualizationPlan


class VisualizationRecommenderPlugin(ABC):
    """Proposes however many VisualizationSpecs the evidence warrants —
    optimizes communication quality, not plot count."""

    strategy_name: str

    @abstractmethod
    async def recommend(
        self,
        insights: BusinessInsights,
        analytics: AnalyticsResult,
        session_id: str | None = None,
    ) -> VisualizationPlan: ...
