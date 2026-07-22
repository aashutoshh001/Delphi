"""UnderstandingEngine backed by LangChain Deep Agents: planning + tool use
over the org profile and data landscape before synthesizing a narrative. This
is the one place in the pipeline where a heavier agent harness earns its
keep — everywhere else stays a plain structured LLM call or explicit
LangGraph node."""

from __future__ import annotations

from hypothesis_agent.adapters.understanding.direct_llm_understanding_engine import (
    UnderstandingExtractionResponse,
)
from hypothesis_agent.contracts.llm import LLMMessage, LLMRequest
from hypothesis_agent.contracts.organization import (
    EmployeeDataLandscape,
    OrganizationProfile,
    OrganizationUnderstanding,
)
from hypothesis_agent.ports.llm_service import LLMService
from hypothesis_agent.ports.understanding_engine import UnderstandingEngine


def _extract_last_message_text(result: dict) -> str:
    messages = result.get("messages", [])
    if not messages:
        return ""
    last = messages[-1]
    content = getattr(last, "content", None)
    if content is None and isinstance(last, dict):
        content = last.get("content")
    return content or ""


class DeepAgentUnderstandingEngine(UnderstandingEngine):
    """Runs a Deep Agent (with two read-only tools exposing the already-fetched
    profile/landscape) to synthesize a narrative, then normalizes its free-form
    output into `OrganizationUnderstanding` via one structured extraction call
    — Deep Agents don't guarantee structured output, so the contract boundary
    is enforced on our side, not assumed from the framework."""

    engine_name = "deep_agent"

    def __init__(
        self,
        llm_service: LLMService,
        deep_agent_model: str = "openai:gpt-4.1-mini",
    ) -> None:
        try:
            from deepagents import create_deep_agent
        except ImportError as exc:
            raise ImportError(
                "DeepAgentUnderstandingEngine requires the 'deepagents' package: "
                "install hypothesis_agent[deep-agents]"
            ) from exc
        self._create_deep_agent = create_deep_agent
        self._deep_agent_model = deep_agent_model
        self._llm = llm_service

    async def understand(
        self, profile: OrganizationProfile, landscape: EmployeeDataLandscape
    ) -> OrganizationUnderstanding:
        profile_json = profile.model_dump_json(indent=2)
        landscape_json = landscape.model_dump_json(indent=2)

        def get_organization_metadata() -> str:
            """Return known structural/strategic metadata for this organization."""
            return profile_json

        def get_data_landscape_summary() -> str:
            """Return which employee data attribute categories exist and their coverage."""
            return landscape_json

        agent = self._create_deep_agent(
            model=self._deep_agent_model,
            tools=[get_organization_metadata, get_data_landscape_summary],
            system_prompt=(
                "You are a senior management consultant and organizational "
                "psychologist. Use your tools to gather this organization's "
                "metadata and data landscape, then write a sharp strategic "
                "narrative covering structural tensions, strategic priorities, "
                "and notable data signals worth pursuing in a hypothesis search. "
                "Do not describe the data — interpret it."
            ),
        )
        result = await agent.ainvoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            f"Understand organization '{profile.organization_id}' "
                            "and produce the strategic narrative."
                        ),
                    }
                ]
            }
        )
        notes = _extract_last_message_text(result)

        extraction_request = LLMRequest(
            messages=[
                LLMMessage(
                    role="system",
                    content=(
                        "Extract the requested fields from the analyst's notes below. "
                        "Do not invent information the notes don't support."
                    ),
                ),
                LLMMessage(
                    role="user",
                    content=(
                        f"Analyst notes:\n{notes}\n\n"
                        "Extract: a 3-6 sentence narrative, key_tensions (list), "
                        "strategic_priorities (list), notable_data_signals (list)."
                    ),
                ),
            ],
            temperature=0.0,
        )
        extracted = await self._llm.complete_structured(extraction_request, UnderstandingExtractionResponse)
        return OrganizationUnderstanding(
            organization_id=profile.organization_id,
            narrative=extracted.narrative,
            key_tensions=extracted.key_tensions,
            strategic_priorities=extracted.strategic_priorities,
            notable_data_signals=extracted.notable_data_signals,
            engine_used=self.engine_name,
        )
