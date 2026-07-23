from __future__ import annotations

from scipy import stats

from insight_pipeline.adapters.employee_data.handle_cache import InMemoryDatasetHandleCache
from insight_pipeline.contracts.analytics import AnalysisMethodResult
from insight_pipeline.contracts.dataset import DatasetHandle, DatasetMetadata
from insight_pipeline.contracts.investigation import InvestigationPlan
from insight_pipeline.plugins.analysis_methods._column_matching import (
    matched_variables,
    numeric_column,
)
from insight_pipeline.plugins.analysis_methods.base import AnalysisMethodPlugin


class CorrelationPlugin(AnalysisMethodPlugin):
    method_name = "correlation"

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
                interpretation_notes="No two matched numeric variables were available.",
                caveats=["skipped — insufficient numeric variables"],
            )
        (var_a, col_a), (var_b, col_b) = pair
        series_a = numeric_column(df, col_a)
        series_b = numeric_column(df, col_b)
        paired = list(zip(series_a, series_b))
        paired = [(a, b) for a, b in paired if a == a and b == b]  # drop NaNs
        if len(paired) < 3:
            return AnalysisMethodResult(
                method=self.method_name,
                variables_involved=[col_a, col_b],
                interpretation_notes="Not enough non-missing paired observations to compute correlation.",
                caveats=["insufficient data"],
            )
        xs, ys = zip(*paired)
        r, p_value = stats.pearsonr(xs, ys)
        strength = "weak" if abs(r) < 0.3 else "moderate" if abs(r) < 0.6 else "strong"
        direction = "positive" if r > 0 else "negative"
        return AnalysisMethodResult(
            method=self.method_name,
            variables_involved=[col_a, col_b],
            statistic=round(float(r), 4),
            p_value=round(float(p_value), 6),
            interpretation_notes=(
                f"Pearson correlation between {col_a} and {col_b} is {strength} and {direction} "
                f"(r={r:.3f}, n={len(paired)})."
            ),
            caveats=["correlation does not establish causation"],
        )
