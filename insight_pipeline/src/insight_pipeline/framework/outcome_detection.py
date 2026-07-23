"""Classifies every column of a (possibly widening) sheet at load time.
Handles the "one sheet, more columns over time" data shape from
docs/NEXT_VERSION_INTEGRATION_PLAN.md / the V2 architecture plan Part 5: a
newly-added column is classified on the next load with zero code change —
either it matches a known assessment pattern (schema.py), matches the
outcome name/pattern list below, or it's reported as UNKNOWN and never
silently analyzed."""

from __future__ import annotations

import re

import pandas as pd
from pydantic import BaseModel, Field

from insight_pipeline.framework.schema import MetricDefinition, MetricFamily, build_metric_definition

# Permissive on purpose (open item #1 in the architecture plan — tighten once
# real production sheets confirm exact outcome-column naming). Matched
# case-insensitively against the whole column name.
_OUTCOME_NAME_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"attrition", r"regretted", r"terminat", r"exit", r"resign",
        r"tenure", r"compensation", r"salary", r"pay\b",
        r"promot", r"performance_rating", r"perf_rating", r"performance_score",
        r"bonus", r"rating_actual", r"actual_performance",
    ]
]


class ColumnClassification(BaseModel):
    identity_columns: list[str] = Field(default_factory=list)
    assessment_columns: list[str] = Field(default_factory=list)
    outcome_columns: list[str] = Field(default_factory=list)
    unknown_columns: list[str] = Field(default_factory=list)
    definitions: dict[str, MetricDefinition] = Field(default_factory=dict)

    def present_names(self) -> set[str]:
        return set(self.definitions.keys())


def _looks_like_outcome(name: str) -> bool:
    return any(pattern.search(name) for pattern in _OUTCOME_NAME_PATTERNS)


def classify_columns(df: pd.DataFrame) -> ColumnClassification:
    result = ColumnClassification()
    for name in df.columns:
        series = df[name]
        coverage = 1.0 - (series.isna().mean() if len(series) else 0.0)
        is_numeric = pd.api.types.is_numeric_dtype(series)
        scale_min = float(series.min()) if is_numeric and series.notna().any() else None
        scale_max = float(series.max()) if is_numeric and series.notna().any() else None

        definition = build_metric_definition(
            name, scale_min=scale_min, scale_max=scale_max, coverage_ratio=coverage
        )

        # A name-pattern outcome match wins even if it happened to match an
        # assessment regex (defensive; today's known families don't collide
        # with the outcome patterns, but new sheet columns might).
        if definition.family is MetricFamily.UNKNOWN and _looks_like_outcome(name):
            definition = definition.model_copy(update={"family": MetricFamily.OUTCOME})

        result.definitions[name] = definition
        if definition.family is MetricFamily.IDENTITY:
            result.identity_columns.append(name)
        elif definition.family is MetricFamily.OUTCOME:
            result.outcome_columns.append(name)
        elif definition.family is MetricFamily.UNKNOWN:
            result.unknown_columns.append(name)
        else:
            result.assessment_columns.append(name)
    return result
