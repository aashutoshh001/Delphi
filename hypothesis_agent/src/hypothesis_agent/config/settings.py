"""Configuration design: a versioned YAML file provides defaults; individual
fields are overridable via `HYPOTHESIS_AGENT__SECTION__FIELD` environment
variables (e.g. `HYPOTHESIS_AGENT__SEARCH__MAX_ITERATIONS=12`). No secrets
live here — API keys are read directly by adapters from their own env vars
(e.g. `OPENAI_API_KEY`)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator

_DEFAULT_YAML = Path(__file__).parent / "default.yaml"
_ENV_PREFIX = "HYPOTHESIS_AGENT__"
# hypothesis_agent/src/hypothesis_agent/config/settings.py -> Delphi/ repo root.
# Anchoring relative data paths here (not to the process's cwd) means the
# server behaves the same whether it's launched from Delphi/, from
# hypothesis_agent/, or from anywhere else — no more silently writing to
# (or reading from) the wrong sample_data/ depending on the launch directory.
_REPO_ROOT = Path(__file__).resolve().parents[4]


class SearchSettings(BaseModel):
    max_iterations: int = 8
    convergence_window: int = 3
    convergence_epsilon: float = 0.02
    exploration_floor: float = 0.15
    mutation_probability: float = 0.2
    discard_threshold: float = 0.35
    duplicate_similarity_threshold: float = 0.93
    # None => real, unseeded randomness (production default). Set this for
    # reproducible runs (tests, debugging a specific search trajectory).
    random_seed: int | None = None
    # Off by default: one more LLM call at the end of every run whose only
    # consumer is the (separate, optional) downstream Investigation Pipeline.
    generate_investigation_seed: bool = False


class ScoringSettings(BaseModel):
    weights: dict[str, float] = Field(
        default_factory=lambda: {
            "business_value": 0.16,
            "novelty": 0.14,
            "depth": 0.12,
            "actionability": 0.12,
            "strategic_importance": 0.10,
            "feasibility": 0.08,
            "organizational_impact": 0.10,
            "expected_insight": 0.08,
            "confidence": 0.06,
            "future_extensibility": 0.04,
        }
    )

    @field_validator("weights")
    @classmethod
    def _weights_sum_to_one(cls, value: dict[str, float]) -> dict[str, float]:
        total = sum(value.values())
        if value and abs(total - 1.0) > 1e-6:
            raise ValueError(f"scoring.weights must sum to 1.0, got {total}")
        return value


class FeedbackSettings(BaseModel):
    min_multiplier: float = 0.7
    max_multiplier: float = 1.3
    smoothing: float = 3.0


class BackendsSettings(BaseModel):
    llm: str = "mock"
    embedding: str = "hash"
    understanding_engine: str = "direct_llm"
    critics: list[str] = Field(default_factory=lambda: ["checklist"])
    organization_repository: str = "in_memory"
    employee_repository: str = "in_memory"
    historical_memory_repository: str = "in_memory"
    feedback_repository: str = "in_memory"
    analysis_agent_gateway: str = "noop"
    # Used only by the "json_file" historical_memory_repository/feedback_repository
    # backends. If relative, anchored to the Delphi/ repo root (see
    # _REPO_ROOT / AgentConfig.load below) rather than the process's cwd.
    json_store_path: str = "sample_data/stories.json"


class LLMSettings(BaseModel):
    model: str = "gpt-4.1-nano"
    temperature: float = 0.5


class EmbeddingSettings(BaseModel):
    model: str = "text-embedding-3-small"
    dimensions: int = 256


class LoggingSettings(BaseModel):
    level: str = "INFO"
    structured: bool = True


class AgentConfig(BaseModel):
    search: SearchSettings = Field(default_factory=SearchSettings)
    scoring: ScoringSettings = Field(default_factory=ScoringSettings)
    feedback: FeedbackSettings = Field(default_factory=FeedbackSettings)
    backends: BackendsSettings = Field(default_factory=BackendsSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)

    @classmethod
    def load(cls, path: Path | str | None = None) -> "AgentConfig":
        data = _load_yaml(_DEFAULT_YAML)
        if path is not None:
            data = _deep_merge(data, _load_yaml(Path(path)))
        data = _deep_merge(data, _env_overrides())
        config = cls.model_validate(data)
        config.backends.json_store_path = _anchor_to_repo_root(config.backends.json_store_path)
        return config


def _anchor_to_repo_root(value: str) -> str:
    resolved = Path(value)
    return str(resolved if resolved.is_absolute() else _REPO_ROOT / resolved)


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _env_overrides() -> dict[str, Any]:
    """Builds a nested dict from HYPOTHESIS_AGENT__SECTION__FIELD env vars.
    Values stay as strings; Pydantic coerces them to the target field type."""
    overrides: dict[str, Any] = {}
    for key, raw_value in os.environ.items():
        if not key.startswith(_ENV_PREFIX):
            continue
        path = key[len(_ENV_PREFIX):].lower().split("__")
        cursor = overrides
        for part in path[:-1]:
            cursor = cursor.setdefault(part, {})
        cursor[path[-1]] = raw_value
    return overrides
