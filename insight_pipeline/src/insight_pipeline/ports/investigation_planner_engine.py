from abc import ABC, abstractmethod

from hypothesis_agent.contracts.hypothesis import HypothesisPackage
from insight_pipeline.contracts.investigation import InvestigationPlan
from insight_pipeline.contracts.organization_knowledge import OrganizationKnowledge


class InvestigationPlannerEngine(ABC):
    """Pluggable reasoning strategy behind the Investigation Planner Agent —
    swappable between a Deep-Agents-based implementation (planning +
    sub-task breakdown) and a single structured LLM call, same fallback
    discipline as hypothesis_agent's UnderstandingEngine."""

    @abstractmethod
    async def plan(
        self, hypothesis_package: HypothesisPackage, relevant_knowledge: list[OrganizationKnowledge]
    ) -> InvestigationPlan: ...
