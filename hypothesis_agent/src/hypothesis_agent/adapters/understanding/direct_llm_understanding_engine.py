from __future__ import annotations

from pydantic import BaseModel, Field

from hypothesis_agent.contracts.llm import LLMMessage, LLMRequest
from hypothesis_agent.contracts.organization import (
    EmployeeDataLandscape,
    OrganizationProfile,
    OrganizationUnderstanding,
)
from hypothesis_agent.ports.llm_service import LLMService
from hypothesis_agent.ports.understanding_engine import UnderstandingEngine
from hypothesis_agent.prompts.registry import PromptRegistry


class UnderstandingExtractionResponse(BaseModel):
    narrative: str
    key_tensions: list[str] = Field(default_factory=list)
    strategic_priorities: list[str] = Field(default_factory=list)
    notable_data_signals: list[str] = Field(default_factory=list)


class DirectLLMUnderstandingEngine(UnderstandingEngine):
    """Fallback UnderstandingEngine: one structured LLM call. Always available
    — used when the Deep Agents extra isn't installed or isn't configured."""

    engine_name = "direct_llm"

    def __init__(self, llm_service: LLMService, prompts: PromptRegistry) -> None:
        self._llm = llm_service
        self._prompts = prompts

    async def understand(
        self, profile: OrganizationProfile, landscape: EmployeeDataLandscape
    ) -> OrganizationUnderstanding:
        template = self._prompts.get("understand_organization")
        core_attributes = "\n".join(f"- {k}: {v}" for k, v in profile.core_attributes.items()) or "(none provided)"
        data_categories = "\n".join(
            f"- {f.name} ({f.category}, coverage={f.coverage_ratio})" for f in landscape.available_fields
        ) or "(no known attribute fields)"
        rendered = template.render(
            organization_name=profile.name or profile.organization_id,
            core_attributes=core_attributes,
            data_categories=data_categories,
            employee_count=landscape.employee_count_estimate or "unknown",
        )
        request = LLMRequest(
            messages=[
                LLMMessage(role="system", content=rendered.system),
                LLMMessage(role="user", content=rendered.user),
            ],
            temperature=0.4,
        )
        result = await self._llm.complete_structured(request, UnderstandingExtractionResponse)
        return OrganizationUnderstanding(
            organization_id=profile.organization_id,
            narrative=result.narrative,
            key_tensions=result.key_tensions,
            strategic_priorities=result.strategic_priorities,
            notable_data_signals=result.notable_data_signals,
            engine_used=self.engine_name,
        )
