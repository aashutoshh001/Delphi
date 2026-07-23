"""360-degree multi-rater divergence — V2 architecture plan Part 4D angle 4's
motivating example, as its own discoverable angle (distinct from the general
QuadrantDivergencePlugin: this one specifically looks for >=2 rater
perspectives on the *same* dimension among the grounded variables, e.g.
self-vs-manager, and reports the population-level perception gap plus, when
3+ raters are present, the full rater-consensus spread)."""

from __future__ import annotations

import re

from insight_pipeline.adapters.employee_data.handle_cache import InMemoryDatasetHandleCache
from insight_pipeline.contracts.analytics import AnalysisMethodResult
from insight_pipeline.contracts.dataset import DatasetHandle, DatasetMetadata
from insight_pipeline.contracts.investigation import InvestigationPlan
from insight_pipeline.framework.derived_metrics import gap, rater_consensus_spread
from insight_pipeline.plugins.analysis_methods._column_matching import match_column
from insight_pipeline.plugins.analysis_methods.base import AnalysisMethodPlugin

_RATER_PATTERN = re.compile(r"^360\.(?P<dimension>\d+)_(?P<rater>self|manager|report|colleague|other)$")
_RATER_ORDER = ("self", "manager", "report", "colleague", "other")


def _rater_columns_by_dimension(names: list[str]) -> dict[str, dict[str, str]]:
    grouped: dict[str, dict[str, str]] = {}
    for name in names:
        match = _RATER_PATTERN.match(name)
        if not match:
            continue
        grouped.setdefault(match.group("dimension"), {})[match.group("rater")] = name
    return grouped


class RaterGapPlugin(AnalysisMethodPlugin):
    method_name = "rater_gap_360"

    def __init__(self, handle_cache: InMemoryDatasetHandleCache) -> None:
        self._handle_cache = handle_cache

    def _best_dimension(self, plan: InvestigationPlan, df) -> tuple[str, dict[str, str]] | None:
        matched_names = [match_column(df, v.name) for v in plan.variables_required]
        matched_names = [n for n in matched_names if n is not None]
        grouped = _rater_columns_by_dimension(matched_names)
        # Prefer the dimension with the most rater perspectives present.
        best = max(grouped.items(), key=lambda kv: len(kv[1]), default=None)
        if best is None or len(best[1]) < 2:
            return None
        return best

    async def is_applicable(self, plan: InvestigationPlan, metadata: DatasetMetadata) -> bool:
        grouped = _rater_columns_by_dimension([f.name for f in metadata.fields])
        return any(len(raters) >= 2 for raters in grouped.values())

    async def run(self, handle: DatasetHandle, plan: InvestigationPlan) -> AnalysisMethodResult:
        df = self._handle_cache.load(handle)
        found = self._best_dimension(plan, df)
        if found is None:
            return AnalysisMethodResult(
                method=self.method_name,
                interpretation_notes="No grounded 360 dimension had 2+ rater perspectives among the requested variables.",
                caveats=["skipped — insufficient rater columns"],
            )
        dimension, raters = found
        ordered = [(r, raters[r]) for r in _RATER_ORDER if r in raters]
        columns_involved = [c for _, c in ordered]

        primary_rater, primary_col = ordered[0]
        other_rater, other_col = ordered[1]
        divergence = gap(df, primary_col, other_col).dropna()
        if divergence.empty:
            return AnalysisMethodResult(
                method=self.method_name,
                variables_involved=columns_involved,
                interpretation_notes="No non-missing paired ratings for this 360 dimension.",
                caveats=["insufficient data"],
            )

        mean_gap = float(divergence.mean())
        std_gap = float(divergence.std()) if len(divergence) > 1 else 0.0
        direction = f"rates themselves higher than {other_rater} does" if mean_gap > 0 else f"rates themselves lower than {other_rater} does"

        notes = [
            f"360 dimension {dimension}: {primary_rater} vs {other_rater} gap, n={len(divergence)}. "
            f"Mean gap = {mean_gap:.3f} (std={std_gap:.3f}) — on average, {primary_rater} {direction}."
        ]
        if len(ordered) >= 3:
            spread = rater_consensus_spread(df, columns_involved).dropna()
            if not spread.empty:
                notes.append(
                    f"Across all {len(ordered)} rater perspectives present ({', '.join(r for r, _ in ordered)}), "
                    f"mean cross-rater spread (std) = {float(spread.mean()):.3f} — higher values mean raters "
                    "disagree more about this person, independent of any single pair's direction."
                )

        return AnalysisMethodResult(
            method=self.method_name,
            variables_involved=columns_involved,
            statistic=round(mean_gap, 4),
            effect_size=round(std_gap, 4),
            interpretation_notes=" ".join(notes),
            caveats=["a self/observer rating gap is a perception difference, not proof of a performance difference"],
        )
