from abc import ABC, abstractmethod

from insight_pipeline.contracts.analytics import AnalyticsResult
from insight_pipeline.contracts.organization_knowledge import OrganizationKnowledge
from insight_pipeline.contracts.root_cause import RootCauseGraph


class BusinessEvaluatorContext:
    def __init__(
        self,
        analytics: AnalyticsResult,
        root_cause: RootCauseGraph,
        knowledge: list[OrganizationKnowledge],
    ) -> None:
        self.analytics = analytics
        self.root_cause = root_cause
        self.knowledge = knowledge


class BusinessEvaluatorPlugin(ABC):
    """One "consulting lens" (financial, risk, opportunity, ROI, ...).
    Each returns a partial contribution merged into one BusinessInsights."""

    lens_name: str

    @abstractmethod
    async def evaluate(self, context: BusinessEvaluatorContext) -> dict: ...
