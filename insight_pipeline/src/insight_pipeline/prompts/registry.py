"""Reuses hypothesis_agent's generic PromptRegistry/PromptTemplate (zero
Hypothesis-Agent-specific coupling) pointed at this package's own templates."""

from __future__ import annotations

from pathlib import Path

from hypothesis_agent.prompts.registry import PromptRegistry, PromptTemplate, RenderedPrompt

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def default_prompt_registry() -> PromptRegistry:
    return PromptRegistry.load_from_directory(_TEMPLATES_DIR)


__all__ = ["PromptRegistry", "PromptTemplate", "RenderedPrompt", "default_prompt_registry"]
