from abc import ABC, abstractmethod

from hypothesis_agent.contracts.organization import (
    EmployeeDataLandscape,
    OrganizationProfile,
    OrganizationUnderstanding,
)


class UnderstandingEngine(ABC):
    """Pluggable reasoning strategy behind the `understand_organization` node.
    Swappable between a Deep-Agents-based implementation (planning + sub-agent
    delegation) and a single structured LLM call, with identical output."""

    @abstractmethod
    async def understand(
        self, profile: OrganizationProfile, landscape: EmployeeDataLandscape
    ) -> OrganizationUnderstanding: ...
