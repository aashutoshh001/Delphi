"""Every plugin family here uses the Hypothesis Agent's own generic
PluginRegistry[T] — reused, not reimplemented, since it has zero
Hypothesis-Agent-specific coupling. See docs/PLATFORM_ARCHITECTURE.md §21."""

from hypothesis_agent.plugins.registry import (
    PluginAlreadyRegisteredError,
    PluginNotFoundError,
    PluginRegistry,
)

__all__ = ["PluginAlreadyRegisteredError", "PluginNotFoundError", "PluginRegistry"]
