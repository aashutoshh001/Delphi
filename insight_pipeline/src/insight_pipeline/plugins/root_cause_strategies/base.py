from abc import ABC, abstractmethod

from insight_pipeline.contracts.analytics import AnalyticsResult
from insight_pipeline.contracts.investigation import InvestigationPlan
from insight_pipeline.contracts.organization_knowledge import OrganizationKnowledge
from insight_pipeline.contracts.root_cause import RootCauseGraph


class RootCauseStrategyPlugin(ABC):
    """One strategy for proposing causal structure (LLM mechanism
    brainstorming, statistical mediation-driven, future structure-learning
    algorithms). Pluggable, uniform interface."""

    strategy_name: str

    @abstractmethod
    async def discover(
        self,
        plan: InvestigationPlan,
        analytics: AnalyticsResult,
        knowledge: list[OrganizationKnowledge],
    ) -> RootCauseGraph: ...
