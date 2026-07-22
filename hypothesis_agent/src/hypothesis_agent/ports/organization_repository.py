from abc import ABC, abstractmethod

from hypothesis_agent.contracts.organization import OrganizationProfile


class OrganizationRepository(ABC):
    """Source of structural/strategic organization metadata. No fixed schema —
    implementations may back onto an HR system, a config file, or (today) an
    in-memory fixture."""

    @abstractmethod
    async def get_profile(self, organization_id: str) -> OrganizationProfile: ...
