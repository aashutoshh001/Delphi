from __future__ import annotations

from hypothesis_agent.contracts.hypothesis import CritiqueResult, HypothesisCandidate
from hypothesis_agent.contracts.llm import LLMMessage, LLMRequest
from hypothesis_agent.plugins.critics.base import Critic, CriticContext
from hypothesis_agent.ports.llm_service import LLMService
from hypothesis_agent.prompts.registry import PromptRegistry


class _ChecklistResponse(CritiqueResult):
    pass


class ChecklistCritic(Critic):
    """Default critic: puts the internal-critic checklist questions to the
    LLM as a single structured call."""

    name = "checklist_critic"

    def __init__(self, llm_service: LLMService, prompts: PromptRegistry) -> None:
        self._llm = llm_service
        self._prompts = prompts

    async def critique(
        self, candidate: HypothesisCandidate, context: CriticContext
    ) -> CritiqueResult:
        template = self._prompts.get("critique")
        similar_summaries = "\n".join(
            f"- {r.statement}" for r in context.similar_prior
        ) or "(none found)"
        rendered = template.render(
            statement=candidate.statement,
            mechanism=candidate.mechanism,
            lens=candidate.lens,
            narrative=context.understanding.narrative,
            similar_prior=similar_summaries,
        )
        request = LLMRequest(
            messages=[
                LLMMessage(role="system", content=rendered.system),
                LLMMessage(role="user", content=rendered.user),
            ],
            temperature=0.3,
            metadata={"session_id": context.session_id} if context.session_id else {},
        )
        result = await self._llm.complete_structured(request, _ChecklistResponse)
        result.critic_name = self.name
        result.similar_prior_ids = [r.id for r in context.similar_prior] if result.similar_to_prior else []
        return CritiqueResult(**result.model_dump())
