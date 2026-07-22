"""Config-driven Evaluator: adding a new LLM-scored dimension is a registry
entry + a prompt template, never a new Python class."""

from __future__ import annotations

from pydantic import BaseModel, Field

from hypothesis_agent.contracts.hypothesis import DimensionScore, HypothesisCandidate
from hypothesis_agent.contracts.llm import LLMMessage, LLMRequest
from hypothesis_agent.plugins.evaluators.base import EvaluationContext, Evaluator
from hypothesis_agent.ports.llm_service import LLMService
from hypothesis_agent.prompts.registry import PromptRegistry


class _DimensionScoreResponse(BaseModel):
    value: float = Field(ge=0.0, le=1.0)
    rationale: str


class LLMDimensionEvaluator(Evaluator):
    def __init__(
        self,
        dimension: str,
        llm_service: LLMService,
        prompts: PromptRegistry,
        template_id: str = "estimate_dimension",
    ) -> None:
        self.dimension = dimension
        self._llm = llm_service
        self._prompts = prompts
        self._template_id = template_id

    async def evaluate(
        self, candidate: HypothesisCandidate, context: EvaluationContext
    ) -> DimensionScore:
        template = self._prompts.get(self._template_id)
        rendered = template.render(
            dimension=self.dimension,
            statement=candidate.statement,
            mechanism=candidate.mechanism,
            lens=candidate.lens,
            constructs=", ".join(candidate.target_constructs),
            narrative=context.understanding.narrative,
        )
        request = LLMRequest(
            messages=[
                LLMMessage(role="system", content=rendered.system),
                LLMMessage(role="user", content=rendered.user),
            ],
            temperature=0.2,
        )
        result = await self._llm.complete_structured(request, _DimensionScoreResponse)
        return DimensionScore(
            dimension=self.dimension,
            value=result.value,
            rationale=result.rationale,
            evaluator="llm_dimension_evaluator",
        )
