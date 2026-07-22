from __future__ import annotations

from hypothesis_agent.contracts.organization import EmployeeDataLandscape
from hypothesis_agent.ports.employee_repository import EmployeeRepository


class InMemoryEmployeeRepository(EmployeeRepository):
    """Fixture-backed landscape repository. Returns an empty landscape for
    unknown organizations — the agent must still function with zero known
    data fields."""

    def __init__(self, landscapes: dict[str, EmployeeDataLandscape] | None = None) -> None:
        self._landscapes = dict(landscapes or {})

    def add(self, landscape: EmployeeDataLandscape) -> None:
        self._landscapes[landscape.organization_id] = landscape

    async def get_data_landscape(self, organization_id: str) -> EmployeeDataLandscape:
        return self._landscapes.get(
            organization_id, EmployeeDataLandscape(organization_id=organization_id)
        )
