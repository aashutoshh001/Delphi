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


class RegressionPlugin(AnalysisMethodPlugin):
    """Simple (single-predictor) linear regression — a first pass; multiple
    regression is future work (docs/PLATFORM_ARCHITECTURE.md §23 phase 12)."""

    method_name = "simple_linear_regression"

    def __init__(self, handle_cache: InMemoryDatasetHandleCache) -> None:
        self._handle_cache = handle_cache

    def _predictor_and_outcome(self, plan: InvestigationPlan, df) -> tuple | None:
        matched = matched_variables(df, plan.variables_required)
        numeric = [(v, c) for v, c in matched if v.expected_type in ("numeric", "ordinal")]
        independents = [(v, c) for v, c in numeric if v.role == "independent"]
        dependents = [(v, c) for v, c in numeric if v.role == "dependent"]
        if not independents or not dependents:
            return None
        return independents[0], dependents[0]

    async def is_applicable(self, plan: InvestigationPlan, metadata: DatasetMetadata) -> bool:
        roles = {v.role for v in plan.variables_required}
        return "independent" in roles and "dependent" in roles

    async def run(self, handle: DatasetHandle, plan: InvestigationPlan) -> AnalysisMethodResult:
        df = self._handle_cache.load(handle)
        pair = self._predictor_and_outcome(plan, df)
        if pair is None:
            return AnalysisMethodResult(
                method=self.method_name,
                interpretation_notes="No matched independent/dependent numeric variable pair found.",
                caveats=["skipped — missing predictor or outcome"],
            )
        (predictor_var, x_col), (outcome_var, y_col) = pair
        xs = numeric_column(df, x_col)
        ys = numeric_column(df, y_col)
        paired = [(x, y) for x, y in zip(xs, ys) if x == x and y == y]
        if len(paired) < 3:
            return AnalysisMethodResult(
                method=self.method_name,
                variables_involved=[x_col, y_col],
                interpretation_notes="Not enough non-missing paired observations to fit a regression.",
                caveats=["insufficient data"],
            )
        xs_clean, ys_clean = zip(*paired)
        result = stats.linregress(xs_clean, ys_clean)
        ci_half_width = 1.96 * result.stderr
        return AnalysisMethodResult(
            method=self.method_name,
            variables_involved=[x_col, y_col],
            statistic=round(float(result.slope), 4),
            p_value=round(float(result.pvalue), 6),
            effect_size=round(float(result.rvalue) ** 2, 4),
            confidence_interval=(
                round(result.slope - ci_half_width, 4),
                round(result.slope + ci_half_width, 4),
            ),
            interpretation_notes=(
                f"A one-unit increase in {x_col} is associated with a "
                f"{result.slope:.3f}-unit change in {y_col} (R²={result.rvalue ** 2:.3f}, "
                f"n={len(paired)})."
            ),
            caveats=["single-predictor model — omitted-variable bias likely", "association, not causation"],
        )
