"""Critic backed by the Strands SDK: an alternate implementation of the same
`Critic` interface as `ChecklistCritic`, useful once the critic needs real
tool orchestration (e.g. a future duplicate-detection service) and built-in
tracing. Selectable in config, chainable with the default critic — not a
replacement requirement."""

from __future__ import annotations

from typing import Any

from hypothesis_agent.contracts.hypothesis import CritiqueResult, HypothesisCandidate
from hypothesis_agent.plugins.critics.base import Critic, CriticContext


class StrandsCriticOrchestrator(Critic):
    name = "strands_critic"

    def __init__(self, model: Any | None = None) -> None:
        try:
            from strands import Agent
        except ImportError as exc:
            raise ImportError(
                "StrandsCriticOrchestrator requires the 'strands-agents' package: "
                "install hypothesis_agent[strands]"
            ) from exc
        self._agent = Agent(model=model) if model is not None else Agent()

    async def critique(
        self, candidate: HypothesisCandidate, context: CriticContext
    ) -> CritiqueResult:
        similar = "\n".join(f"- {r.statement}" for r in context.similar_prior) or "(none found)"
        prompt = (
            "Critique this organizational hypothesis as a skeptical internal reviewer.\n\n"
            f"Organizational narrative:\n{context.understanding.narrative}\n\n"
            f"Hypothesis (lens: {candidate.lens}): {candidate.statement}\n"
            f"Mechanism: {candidate.mechanism}\n\n"
            f"Similar historical hypotheses:\n{similar}\n\n"
            "Consider: Is this obvious? Would executives care? Does it create an "
            "actionable decision? Is it similar to something already generated? "
            "Does it reveal a hidden mechanism? Could a downstream analysis agent "
            "plausibly test it? List concrete issues and improvements."
        )
        result = await self._agent.structured_output_async(CritiqueResult, prompt)
        result.critic_name = self.name
        return result
