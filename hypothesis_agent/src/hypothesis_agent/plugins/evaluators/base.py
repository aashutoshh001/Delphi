from abc import ABC, abstractmethod

from hypothesis_agent.contracts.hypothesis import DimensionScore, HypothesisCandidate
from hypothesis_agent.contracts.organization import OrganizationUnderstanding


class EvaluationContext:
    """Everything an Evaluator may condition on, beyond the candidate itself."""

    def __init__(
        self,
        understanding: OrganizationUnderstanding,
        landscape_categories: set[str],
        archive: list[HypothesisCandidate],
        session_id: str | None = None,
    ) -> None:
        self.understanding = understanding
        self.landscape_categories = landscape_categories
        self.archive = archive
        self.session_id = session_id


class Evaluator(ABC):
    """Scores one `EvaluationScorecard` dimension. Implementations may be
    LLM-backed (`LLMDimensionEvaluator`) or purely rule-based — the search
    loop treats both identically."""

    dimension: str

    @abstractmethod
    async def evaluate(
        self, candidate: HypothesisCandidate, context: EvaluationContext
    ) -> DimensionScore: ...
