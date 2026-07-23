"""Config design mirrors hypothesis_agent's: YAML defaults + per-field
HYPOTHESIS... no — INSIGHT_PIPELINE__SECTION__FIELD env overrides, deep-merged.
LLM/embedding backends are NOT configured here — insight_pipeline reuses
whatever hypothesis_agent.di.container already built (one LLM configuration
for the whole platform, not two)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

_DEFAULT_YAML = Path(__file__).parent / "default.yaml"
_ENV_PREFIX = "INSIGHT_PIPELINE__"
# insight_pipeline/src/insight_pipeline/config/settings.py -> Delphi/ repo root.
# Anchoring relative data paths here (not to the process's cwd) means the
# server behaves the same regardless of the directory it's launched from —
# see the matching _REPO_ROOT in hypothesis_agent/config/settings.py.
_REPO_ROOT = Path(__file__).resolve().parents[4]


class BackendsSettings(BaseModel):
    organization_knowledge_repository: str = "in_memory"
    organization_knowledge_retriever: str = "embedding"
    employee_data_repository: str = "excel"
    query_planner: str = "grounded"
    plotting_engine: str = "matplotlib"
    insight_package_repository: str = "json_file"
    root_cause_strategy: str = "direct_llm"
    construct_grounding_engine: str = "direct_llm"
    # If relative, anchored to the Delphi/ repo root (see _REPO_ROOT /
    # PipelineConfig.load below) rather than the process's cwd.
    excel_path: str = "Book1_standardized.xlsx"
    insight_store_path: str = "sample_data/insights.json"


class AnalyticsSettings(BaseModel):
    significance_threshold: float = 0.05
    max_methods_per_investigation: int = 6


class VisualizationSettings(BaseModel):
    max_figures_per_report: int = 6
    # If relative, anchored to the Delphi/ repo root — see excel_path above.
    figure_output_dir: str = "sample_data/insights/figures"


class LoggingSettings(BaseModel):
    level: str = "INFO"
    structured: bool = True


class PipelineConfig(BaseModel):
    backends: BackendsSettings = Field(default_factory=BackendsSettings)
    analytics: AnalyticsSettings = Field(default_factory=AnalyticsSettings)
    visualization: VisualizationSettings = Field(default_factory=VisualizationSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)

    @classmethod
    def load(cls, path: Path | str | None = None) -> "PipelineConfig":
        data = _load_yaml(_DEFAULT_YAML)
        if path is not None:
            data = _deep_merge(data, _load_yaml(Path(path)))
        data = _deep_merge(data, _env_overrides())
        config = cls.model_validate(data)
        config.backends.excel_path = _anchor_to_repo_root(config.backends.excel_path)
        config.backends.insight_store_path = _anchor_to_repo_root(config.backends.insight_store_path)
        config.visualization.figure_output_dir = _anchor_to_repo_root(config.visualization.figure_output_dir)
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
