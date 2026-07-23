"""Default ConstructGroundingEngine: one structured LLM call, then a
deterministic code-level filter against the real FrameworkRegistry — the
same "don't rely on the LLM alone" discipline hypothesis_agent's dedup guard
uses (critique.py). The LLM is told (prompt) to only use real names; this
adapter then verifies it, rather than trusting it. Any column name the LLM
proposes that isn't real is dropped and recorded in
`GroundingMap.rejected_column_names` — it never reaches a construct's
`columns` list, regardless of what the LLM said."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from hypothesis_agent.contracts.hypothesis import HypothesisPackage
from hypothesis_agent.contracts.llm import LLMMessage, LLMRequest
from hypothesis_agent.ports.llm_service import LLMService

from insight_pipeline.contracts.grounding import GroundedConstruct, GroundingMap, UngroundedConstruct
from insight_pipeline.framework.registry import FrameworkRegistry
from insight_pipeline.ports.construct_grounding_engine import ConstructGroundingEngine
from insight_pipeline.prompts.registry import PromptRegistry

_ROLE = Literal["independent", "dependent", "moderator", "mediator", "control", "context"]


class _GroundedConstructResponse(BaseModel):
    construct_name: str
    columns: list[str] = Field(default_factory=list)
    role: _ROLE = "context"
    rationale: str = ""


class _UngroundedConstructResponse(BaseModel):
    construct_name: str
    reason: str = ""


class _GroundingResponse(BaseModel):
    grounded: list[_GroundedConstructResponse] = Field(default_factory=list)
    ungrounded: list[_UngroundedConstructResponse] = Field(default_factory=list)


class DirectLLMConstructGroundingEngine(ConstructGroundingEngine):
    engine_name = "direct_llm"

    def __init__(self, llm_service: LLMService, prompts: PromptRegistry) -> None:
        self._llm = llm_service
        self._prompts = prompts

    async def ground(
        self, hypothesis_package: HypothesisPackage, registry: FrameworkRegistry
    ) -> GroundingMap:
        template = self._prompts.get("construct_grounding")
        rendered = template.render(
            statement=hypothesis_package.hypothesis_statement,
            mechanism=hypothesis_package.mechanism_explanation,
            constructs=", ".join(hypothesis_package.target_constructs) or "(none listed)",
            available_columns=registry.describe_for_prompt(registry.all_assessment_columns()),
            outcome_columns=registry.describe_for_prompt(registry.all_outcome_columns()) or "(none available)",
        )
        request = LLMRequest(
            messages=[
                LLMMessage(role="system", content=rendered.system),
                LLMMessage(role="user", content=rendered.user),
            ],
            temperature=0.2,
        )
        response = await self._llm.complete_structured(request, _GroundingResponse)

        grounded: list[GroundedConstruct] = []
        ungrounded: list[UngroundedConstruct] = [
            UngroundedConstruct(construct_name=u.construct_name, reason=u.reason) for u in response.ungrounded
        ]
        rejected: list[str] = []

        for item in response.grounded:
            valid_columns = [c for c in item.columns if registry.is_real_column(c)]
            invalid_columns = [c for c in item.columns if not registry.is_real_column(c)]
            rejected.extend(invalid_columns)
            if not valid_columns:
                reason = (
                    "LLM proposed only non-existent column(s) for this construct: "
                    f"{invalid_columns}" if invalid_columns else "No columns proposed."
                )
                ungrounded.append(UngroundedConstruct(construct_name=item.construct_name, reason=reason))
                continue
            grounded.append(
                GroundedConstruct(
                    construct_name=item.construct_name,
                    columns=valid_columns,
                    role=item.role,
                    rationale=item.rationale,
                )
            )

        return GroundingMap(
            hypothesis_package_id=hypothesis_package.package_id,
            grounded=grounded,
            ungrounded=ungrounded,
            outcome_columns_available=registry.all_outcome_columns(),
            rejected_column_names=rejected,
            provenance={"engine": self.engine_name},
        )
