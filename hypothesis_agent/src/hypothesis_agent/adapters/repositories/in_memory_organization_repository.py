from __future__ import annotations

from hypothesis_agent.contracts.organization import OrganizationProfile
from hypothesis_agent.ports.organization_repository import OrganizationRepository


class InMemoryOrganizationRepository(OrganizationRepository):
    """Fixture-backed repository. Returns a bare-minimum profile for any
    unknown organization_id rather than raising, so the agent can run before
    any real org is registered."""

    def __init__(self, profiles: dict[str, OrganizationProfile] | None = None) -> None:
        self._profiles = dict(profiles or {})

    def add(self, profile: OrganizationProfile) -> None:
        self._profiles[profile.organization_id] = profile

    async def get_profile(self, organization_id: str) -> OrganizationProfile:
        return self._profiles.get(
            organization_id, OrganizationProfile(organization_id=organization_id)
        )
