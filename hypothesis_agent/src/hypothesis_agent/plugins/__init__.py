from dataclasses import dataclass

from hypothesis_agent.contracts.hypothesis import BusinessLens
from hypothesis_agent.plugins.critics.base import Critic
from hypothesis_agent.plugins.evaluators.base import Evaluator
from hypothesis_agent.plugins.memory_policies.base import FeedbackPriorPolicy
from hypothesis_agent.plugins.registry import PluginRegistry
from hypothesis_agent.plugins.search_heuristics.base import SearchHeuristic


@dataclass
class ReasoningPlugins:
    """Bundles every reasoning-time extension point. Constructed once per
    agent instance by di/container.py; nodes only ever see this bundle, never
    a concrete plugin implementation directly."""

    lenses: PluginRegistry[BusinessLens]
    evaluators: PluginRegistry[Evaluator]
    critics: list[Critic]
    search_heuristic: SearchHeuristic
    memory_policy: FeedbackPriorPolicy


__all__ = ["ReasoningPlugins"]
