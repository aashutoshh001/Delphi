from abc import ABC, abstractmethod

from hypothesis_agent.contracts.hypothesis import CritiqueResult, HypothesisCandidate
from hypothesis_agent.contracts.memory import HistoricalHypothesisRecord
from hypothesis_agent.contracts.organization import OrganizationUnderstanding


class CriticContext:
    def __init__(
        self,
        understanding: OrganizationUnderstanding,
        similar_prior: list[HistoricalHypothesisRecord],
        session_id: str | None = None,
    ) -> None:
        self.understanding = understanding
        self.similar_prior = similar_prior
        self.session_id = session_id


class Critic(ABC):
    """Self-critiques a candidate against the internal-critic checklist
    (obviousness, executive relevance, novelty, actionability, hidden
    mechanism, downstream feasibility)."""

    name: str = "critic"

    @abstractmethod
    async def critique(
        self, candidate: HypothesisCandidate, context: CriticContext
    ) -> CritiqueResult: ...


class CriticChain:
    """Runs several critics and merges results conservatively: any critic
    flagging an issue wins (booleans OR'd where a flag means "bad"), issue
    lists concatenated, so no single lenient critic can wave through a weak
    candidate."""

    def __init__(self, critics: list[Critic]) -> None:
        if not critics:
            raise ValueError("CriticChain requires at least one Critic")
        self._critics = critics

    async def run(self, candidate: HypothesisCandidate, context: CriticContext) -> CritiqueResult:
        results = [await critic.critique(candidate, context) for critic in self._critics]
        merged = results[0].model_copy(deep=True)
        for result in results[1:]:
            merged.is_obvious = merged.is_obvious or result.is_obvious
            merged.similar_to_prior = merged.similar_to_prior or result.similar_to_prior
            merged.creates_actionable_decision = (
                merged.creates_actionable_decision and result.creates_actionable_decision
            )
            merged.reveals_hidden_mechanism = (
                merged.reveals_hidden_mechanism and result.reveals_hidden_mechanism
            )
            merged.downstream_feasible = merged.downstream_feasible and result.downstream_feasible
            merged.similar_prior_ids = list(
                dict.fromkeys(merged.similar_prior_ids + result.similar_prior_ids)
            )
            merged.issues = list(dict.fromkeys(merged.issues + result.issues))
            merged.suggested_improvements = list(
                dict.fromkeys(merged.suggested_improvements + result.suggested_improvements)
            )
        merged.critic_name = "+".join(r.critic_name for r in results)
        return merged
