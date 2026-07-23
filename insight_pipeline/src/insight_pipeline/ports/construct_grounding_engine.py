from abc import ABC, abstractmethod

from hypothesis_agent.contracts.hypothesis import HypothesisPackage

from insight_pipeline.contracts.grounding import GroundingMap
from insight_pipeline.framework.registry import FrameworkRegistry


class ConstructGroundingEngine(ABC):
    """Pluggable reasoning strategy behind the Construct Grounding Agent —
    maps a hypothesis's free-text constructs onto real SHL Metric Framework
    columns, or flags them unmeasurable. Whatever engine implements this,
    the resulting GroundingMap must never contain a column name absent from
    `registry` — see direct_llm_engine.py for where that's enforced."""

    @abstractmethod
    async def ground(
        self, hypothesis_package: HypothesisPackage, registry: FrameworkRegistry
    ) -> GroundingMap: ...
