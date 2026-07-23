from __future__ import annotations

from pydantic import BaseModel, Field

from hypothesis_agent.contracts.hypothesis import HypothesisPackage
from hypothesis_agent.contracts.llm import LLMMessage, LLMRequest
from hypothesis_agent.ports.llm_service import LLMService
from insight_pipeline.contracts.grounding import GroundingMap
from insight_pipeline.contracts.investigation import InvestigationPlan, PopulationSpec, VariableSpec
from insight_pipeline.contracts.organization_knowledge import OrganizationKnowledge
from insight_pipeline.ports.investigation_planner_engine import InvestigationPlannerEngine
from insight_pipeline.prompts.registry import PromptRegistry


class InvestigationPlanResponse(BaseModel):
    variables_required: list[VariableSpec] = Field(default_factory=list)
    target_population: PopulationSpec
    segmentation_strategy: list[str] = Field(default_factory=list)
    potential_confounders: list[str] = Field(default_factory=list)
    filtering_rules: list[str] = Field(default_factory=list)
    statistical_questions: list[str] = Field(default_factory=list)
    business_questions: list[str] = Field(default_factory=list)
    validation_strategy: str = ""
    recommended_analysis_types: list[str] = Field(default_factory=list)
    potential_risks: list[str] = Field(default_factory=list)
    suggested_visualizations: list[str] = Field(default_factory=list)


def render_grounded_columns(grounding_map: GroundingMap) -> str:
    if not grounding_map.grounded:
        return "(nothing grounded)"
    lines = []
    for construct in grounding_map.grounded:
        lines.append(f"- {construct.construct_name} -> {construct.columns} (role: {construct.role})")
    return "\n".join(lines)


def render_ungrounded_constructs(grounding_map: GroundingMap) -> str:
    if not grounding_map.ungrounded:
        return "(none)"
    return "\n".join(f"- {u.construct_name}: {u.reason}" for u in grounding_map.ungrounded)


class DirectLLMInvestigationPlanner(InvestigationPlannerEngine):
    """Fallback / default engine: one structured LLM call, constrained to
    the already-grounded columns (V2 architecture plan Part 4C) — this
    engine never invents a variable name; it only ever arranges real,
    already-verified columns into a plan."""

    engine_name = "direct_llm"

    def __init__(self, llm_service: LLMService, prompts: PromptRegistry) -> None:
        self._llm = llm_service
        self._prompts = prompts

    async def plan(
        self,
        hypothesis_package: HypothesisPackage,
        relevant_knowledge: list[OrganizationKnowledge],
        grounding_map: GroundingMap,
    ) -> InvestigationPlan:
        template = self._prompts.get("investigation_plan")
        knowledge_text = (
            "\n".join(f"- [{k.category}] {k.title}: {k.excerpt}" for k in relevant_knowledge)
            or "(none available)"
        )
        rendered = template.render(
            lens=hypothesis_package.business_lens,
            statement=hypothesis_package.hypothesis_statement,
            mechanism=hypothesis_package.mechanism_explanation,
            proposed_population=hypothesis_package.proposed_population or "(not specified)",
            grounded_columns=render_grounded_columns(grounding_map),
            ungrounded_constructs=render_ungrounded_constructs(grounding_map),
            knowledge=knowledge_text,
        )
        request = LLMRequest(
            messages=[
                LLMMessage(role="system", content=rendered.system),
                LLMMessage(role="user", content=rendered.user),
            ],
            temperature=0.4,
            # Groups every LLM call in this whole investigation into the
            # same Langfuse session as the hypothesis that started it — the
            # frontend already tags package_id with the hypothesis's own
            # session id (see script.js's requestInvestigation), so this is
            # free: no new id, no new parameter, just reusing what's here.
            metadata={"session_id": hypothesis_package.package_id} if hypothesis_package.package_id else {},
        )
        result = await self._llm.complete_structured(request, InvestigationPlanResponse)

        # Deterministic enforcement, same discipline as construct grounding:
        # don't rely on the LLM alone to honor "verbatim from GROUNDED
        # COLUMNS only" — any variable it names that isn't actually grounded
        # is dropped here, never reaches data retrieval.
        allowed = set(grounding_map.all_grounded_columns()) | set(grounding_map.outcome_columns_available)
        variables_required = [v for v in result.variables_required if v.name in allowed]

        return InvestigationPlan(
            hypothesis_package_id=hypothesis_package.package_id,
            organization_id=hypothesis_package.organization_id,
            variables_required=variables_required,
            target_population=result.target_population,
            segmentation_strategy=result.segmentation_strategy,
            potential_confounders=result.potential_confounders,
            filtering_rules=result.filtering_rules,
            statistical_questions=result.statistical_questions,
            business_questions=result.business_questions,
            validation_strategy=result.validation_strategy,
            recommended_analysis_types=result.recommended_analysis_types,
            potential_risks=result.potential_risks,
            suggested_visualizations=result.suggested_visualizations,
            relevant_knowledge=relevant_knowledge,
            provenance={"engine": self.engine_name},
        )
