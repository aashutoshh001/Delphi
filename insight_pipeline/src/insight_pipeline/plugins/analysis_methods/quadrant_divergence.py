"""Flagship multi-angle method — V2 architecture plan Part 4D angle 4 /
Part 4F chart. Picks any two matched numeric/ordinal grounded variables,
computes a quadrant split around each column's own midpoint, and reports the
population's divergence statistics (off-diagonal ratio, mean/std gap). This
is the general mechanism behind the HiPo scatter, an
Invest/Leverage/Reconsider/Redirect-style fit-vs-experience view, and — the
motivating example — a 360 self-vs-manager rating gap: whichever two
grounded dimensions the Investigation Planner selected, the divergence
between them is itself the finding."""

from __future__ import annotations

from insight_pipeline.adapters.employee_data.handle_cache import InMemoryDatasetHandleCache
from insight_pipeline.contracts.analytics import AnalysisMethodResult
from insight_pipeline.contracts.dataset import DatasetHandle, DatasetMetadata
from insight_pipeline.contracts.investigation import InvestigationPlan
from insight_pipeline.framework.derived_metrics import quadrant_divergence
from insight_pipeline.plugins.analysis_methods._column_matching import (
    matched_variables,
    numeric_column,
)
from insight_pipeline.plugins.analysis_methods.base import AnalysisMethodPlugin


class QuadrantDivergencePlugin(AnalysisMethodPlugin):
    method_name = "quadrant_divergence"

    def __init__(self, handle_cache: InMemoryDatasetHandleCache) -> None:
        self._handle_cache = handle_cache

    def _numeric_pair(self, plan: InvestigationPlan, df) -> tuple | None:
        matched = matched_variables(df, plan.variables_required)
        numeric = [(v, c) for v, c in matched if v.expected_type in ("numeric", "ordinal")]
        if len(numeric) < 2:
            return None
        return numeric[0], numeric[1]

    async def is_applicable(self, plan: InvestigationPlan, metadata: DatasetMetadata) -> bool:
        numeric_fields = [f for f in metadata.fields if f.data_type in ("numeric", "ordinal")]
        return len(numeric_fields) >= 2

    async def run(self, handle: DatasetHandle, plan: InvestigationPlan) -> AnalysisMethodResult:
        df = self._handle_cache.load(handle)
        pair = self._numeric_pair(plan, df)
        if pair is None:
            return AnalysisMethodResult(
                method=self.method_name,
                interpretation_notes="No two matched numeric/ordinal grounded variables were available for a quadrant comparison.",
                caveats=["skipped — insufficient numeric variables"],
            )
        (var_a, col_a), (var_b, col_b) = pair
        working = df[[col_a, col_b]].copy()
        working[col_a] = numeric_column(df, col_a)
        working[col_b] = numeric_column(df, col_b)
        working = working.dropna()
        if len(working) < 3:
            return AnalysisMethodResult(
                method=self.method_name,
                variables_involved=[col_a, col_b],
                interpretation_notes="Not enough non-missing paired observations for a quadrant comparison.",
                caveats=["insufficient data"],
            )

        # Threshold = midpoint of each column's own observed range — a
        # dimension-agnostic default that works whether the pair is on a 1-5
        # scale, a 0-1 percentile, or anything else, without assuming a
        # specific SHL scale convention.
        x_threshold = float((working[col_a].min() + working[col_a].max()) / 2)
        y_threshold = float((working[col_b].min() + working[col_b].max()) / 2)

        result = quadrant_divergence(
            working, x_column=col_a, y_column=col_b, x_threshold=x_threshold, y_threshold=y_threshold
        )

        quadrant_summary = ", ".join(f"{label}: {count}" for label, count in result.quadrant_counts.items())
        direction = "higher on the first" if result.gap_mean > 0 else "higher on the second"
        return AnalysisMethodResult(
            method=self.method_name,
            variables_involved=[col_a, col_b],
            statistic=round(result.off_diagonal_ratio, 4),
            effect_size=round(result.gap_mean, 4),
            interpretation_notes=(
                f"Quadrant split of {col_a} (x, threshold={x_threshold:.2f}) vs {col_b} "
                f"(y, threshold={y_threshold:.2f}), n={len(working)}: {quadrant_summary}. "
                f"Mean gap ({col_a} - {col_b}) = {result.gap_mean:.3f} (std={result.gap_std:.3f}) — "
                f"the population runs {direction} dimension on average. "
                f"{result.off_diagonal_ratio:.0%} of observations sit materially off the x=y diagonal, "
                "i.e. show a real divergence between the two dimensions rather than close agreement."
            ),
            caveats=["thresholds are the observed midpoint of each column, not an SHL-official cut score unless the two columns happen to share one"],
        )
