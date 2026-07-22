from hypothesis_agent.contracts.hypothesis import EVALUATION_DIMENSIONS
from hypothesis_agent.plugins.evaluators.base import EvaluationContext, Evaluator
from hypothesis_agent.plugins.evaluators.feasibility_evaluator import (
    FeasibilityFromLandscapeEvaluator,
)
from hypothesis_agent.plugins.evaluators.llm_dimension_evaluator import (
    LLMDimensionEvaluator,
)
from hypothesis_agent.plugins.registry import PluginRegistry
from hypothesis_agent.ports.llm_service import LLMService
from hypothesis_agent.prompts.registry import PromptRegistry


def default_evaluator_registry(
    llm_service: LLMService, prompts: PromptRegistry
) -> PluginRegistry[Evaluator]:
    """Every dimension defaults to an LLM-scored evaluator except `feasibility`,
    which uses the rule-based landscape evaluator. Swap any single dimension's
    strategy by re-registering it with override=True — no other code changes."""
    registry: PluginRegistry[Evaluator] = PluginRegistry(kind="evaluator")
    for dimension in EVALUATION_DIMENSIONS:
        if dimension == "feasibility":
            registry.register(dimension, FeasibilityFromLandscapeEvaluator())
        else:
            registry.register(dimension, LLMDimensionEvaluator(dimension, llm_service, prompts))
    return registry


__all__ = [
    "EvaluationContext",
    "Evaluator",
    "FeasibilityFromLandscapeEvaluator",
    "LLMDimensionEvaluator",
    "default_evaluator_registry",
]
