from abc import ABC, abstractmethod

from hypothesis_agent.contracts.hypothesis import HypothesisPackage
from insight_pipeline.contracts.grounding import GroundingMap
from insight_pipeline.contracts.investigation import InvestigationPlan
from insight_pipeline.contracts.organization_knowledge import OrganizationKnowledge


class InvestigationPlannerEngine(ABC):
    """Pluggable reasoning strategy behind the Investigation Planner Agent —
    swappable between a Deep-Agents-based implementation (planning +
    sub-task breakdown) and a single structured LLM call, same fallback
    discipline as hypothesis_agent's UnderstandingEngine.

    `grounding_map` (V2 architecture plan Part 4C) constrains
    `variables_required` to real, already-grounded columns — the planner no
    longer invents variable names from the hypothesis text alone."""

    @abstractmethod
    async def plan(
        self,
        hypothesis_package: HypothesisPackage,
        relevant_knowledge: list[OrganizationKnowledge],
        grounding_map: GroundingMap,
    ) -> InvestigationPlan: ...
