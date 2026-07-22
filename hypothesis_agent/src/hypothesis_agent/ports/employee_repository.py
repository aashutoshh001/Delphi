from abc import ABC, abstractmethod

from hypothesis_agent.contracts.organization import EmployeeDataLandscape


class EmployeeRepository(ABC):
    """Source of schema-level employee data descriptions only. Deliberately
    never exposes row-level employee records — that boundary keeps the
    Hypothesis Agent from ever needing PII access, and keeps statistical
    analysis a downstream-agent responsibility."""

    @abstractmethod
    async def get_data_landscape(self, organization_id: str) -> EmployeeDataLandscape: ...
