"""Lookup/query API over one loaded sheet's column classification — the
object every insight-side agent actually talks to. Built fresh per
`DatasetHandle` (cheap: it's just grouping already-classified column names),
never a static global, so it always reflects the columns *actually present*
in whatever sheet was loaded (today's Book1_standardized.xlsx, or a future
wider one)."""

from __future__ import annotations

from collections import defaultdict

import pandas as pd

from insight_pipeline.framework.outcome_detection import ColumnClassification, classify_columns
from insight_pipeline.framework.schema import MetricDefinition, MetricFamily

_RATER_ORDER = ("self", "manager", "report", "colleague", "other")


class FrameworkRegistry:
    def __init__(self, classification: ColumnClassification) -> None:
        self._classification = classification

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame) -> "FrameworkRegistry":
        return cls(classify_columns(df))

    @classmethod
    def from_definitions(cls, definitions: dict[str, MetricDefinition]) -> "FrameworkRegistry":
        classification = ColumnClassification(definitions=definitions)
        for name, definition in definitions.items():
            if definition.family is MetricFamily.IDENTITY:
                classification.identity_columns.append(name)
            elif definition.family is MetricFamily.OUTCOME:
                classification.outcome_columns.append(name)
            elif definition.family is MetricFamily.UNKNOWN:
                classification.unknown_columns.append(name)
            else:
                classification.assessment_columns.append(name)
        return cls(classification)

    # -- basic lookups ----------------------------------------------------

    def is_real_column(self, name: str) -> bool:
        return name in self._classification.definitions

    def get(self, name: str) -> MetricDefinition | None:
        return self._classification.definitions.get(name)

    def all_assessment_columns(self) -> list[str]:
        return list(self._classification.assessment_columns)

    def all_outcome_columns(self) -> list[str]:
        return list(self._classification.outcome_columns)

    def all_identity_columns(self) -> list[str]:
        return list(self._classification.identity_columns)

    def unknown_columns(self) -> list[str]:
        return list(self._classification.unknown_columns)

    def all_present_columns(self) -> list[str]:
        return list(self._classification.definitions.keys())

    def columns_in_family(self, family: MetricFamily) -> list[str]:
        return [
            name
            for name, definition in self._classification.definitions.items()
            if definition.family is family
        ]

    # -- structural groupings (real, verified from column names) ---------

    def gsa_domains(self) -> dict[str, list[str]]:
        """domain number ('1'..'8') -> its GSA skill item columns."""
        grouped: dict[str, list[str]] = defaultdict(list)
        for name in self.columns_in_family(MetricFamily.GSA_SKILL_ITEM):
            domain = self._classification.definitions[name].hierarchy["domain"]
            grouped[domain].append(name)
        return dict(grouped)

    def mq_facets(self) -> dict[str, list[str]]:
        """facet letter -> its raw MQ item columns."""
        grouped: dict[str, list[str]] = defaultdict(list)
        for name in self.columns_in_family(MetricFamily.MOTIVATION_ITEM):
            definition = self._classification.definitions[name]
            if definition.hierarchy.get("variant") != "raw":
                continue
            grouped[definition.hierarchy["facet"]].append(name)
        return dict(grouped)

    def rater_360_dimensions(self) -> dict[str, dict[str, str]]:
        """dimension number ('1'..'8') -> {rater_type: column_name}, rater
        types ordered self/manager/report/colleague/other when present."""
        grouped: dict[str, dict[str, str]] = defaultdict(dict)
        for name in self.columns_in_family(MetricFamily.RATER_360):
            definition = self._classification.definitions[name]
            dimension = definition.hierarchy["dimension"]
            rater = definition.hierarchy["rater"]
            grouped[dimension][rater] = name
        return {
            dim: {r: raters[r] for r in _RATER_ORDER if r in raters}
            for dim, raters in grouped.items()
        }

    # -- prompt injection (base-agents' extract_competency_column_lines pattern) --

    def describe_for_prompt(self, names: list[str] | None = None, limit: int = 200) -> str:
        """Renders real column names + their verified structural semantics
        as prompt lines — the only view of the data any LLM call downstream
        of grounding is ever given. `names=None` describes everything
        present (assessment + outcome), capped at `limit`."""
        if names is None:
            names = self.all_assessment_columns() + self.all_outcome_columns()
        lines = []
        for name in names[:limit]:
            definition = self._classification.definitions.get(name)
            if definition is None:
                continue
            scale = ""
            if definition.scale_min is not None and definition.scale_max is not None:
                scale = f" | range: {definition.scale_min:g}-{definition.scale_max:g}"
            coverage = f" | coverage: {definition.coverage_ratio:.0%}"
            stability = f" | {definition.stability_note}" if definition.stability_note else ""
            lines.append(f"- {name} | {definition.family.value}{scale}{coverage} | {definition.semantic_description}{stability}")
        if len(names) > limit:
            lines.append(f"... ({len(names) - limit} more columns omitted for length)")
        return "\n".join(lines) if lines else "(no columns available)"

    def family_summary(self) -> str:
        """One line per family with counts — a compact orientation view for
        prompts that need to know what KINDS of data exist without every
        column name (e.g. the Investigation Planner picking angles)."""
        counts: dict[MetricFamily, int] = defaultdict(int)
        for definition in self._classification.definitions.values():
            counts[definition.family] += 1
        lines = [f"- {family.value}: {count} column(s)" for family, count in sorted(counts.items(), key=lambda kv: kv[0].value)]
        return "\n".join(lines)
