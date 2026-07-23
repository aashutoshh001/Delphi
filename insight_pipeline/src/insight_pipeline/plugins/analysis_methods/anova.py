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


class ANOVAPlugin(AnalysisMethodPlugin):
    method_name = "one_way_anova"

    def __init__(self, handle_cache: InMemoryDatasetHandleCache) -> None:
        self._handle_cache = handle_cache

    def _group_and_outcome(self, plan: InvestigationPlan, df) -> tuple | None:
        matched = matched_variables(df, plan.variables_required)
        categorical = [(v, c) for v, c in matched if v.expected_type == "categorical"]
        numeric = [(v, c) for v, c in matched if v.expected_type in ("numeric", "ordinal")]
        dependents = [(v, c) for v, c in numeric if v.role == "dependent"] or numeric
        if not categorical or not dependents:
            return None
        return categorical[0], dependents[0]

    async def is_applicable(self, plan: InvestigationPlan, metadata: DatasetMetadata) -> bool:
        has_categorical = any(f.data_type == "categorical" for f in metadata.fields)
        has_numeric = any(f.data_type in ("numeric", "ordinal") for f in metadata.fields)
        return has_categorical and has_numeric

    async def run(self, handle: DatasetHandle, plan: InvestigationPlan) -> AnalysisMethodResult:
        df = self._handle_cache.load(handle)
        pair = self._group_and_outcome(plan, df)
        if pair is None:
            return AnalysisMethodResult(
                method=self.method_name,
                interpretation_notes="No matched categorical grouping variable and numeric outcome found.",
                caveats=["skipped — missing group or outcome variable"],
            )
        (group_var, group_col), (outcome_var, outcome_col) = pair
        outcome = numeric_column(df, outcome_col)
        working = df[[group_col]].copy()
        working["__outcome__"] = outcome
        working = working.dropna()
        groups = [g["__outcome__"].values for _, g in working.groupby(group_col) if len(g) >= 2]
        if len(groups) < 2:
            return AnalysisMethodResult(
                method=self.method_name,
                variables_involved=[group_col, outcome_col],
                interpretation_notes=f"Fewer than 2 usable groups in {group_col} after dropping missing data.",
                caveats=["insufficient group variation"],
            )
        f_stat, p_value = stats.f_oneway(*groups)
        return AnalysisMethodResult(
            method=self.method_name,
            variables_involved=[group_col, outcome_col],
            statistic=round(float(f_stat), 4),
            p_value=round(float(p_value), 6),
            interpretation_notes=(
                f"{outcome_col} differs {'significantly' if p_value < 0.05 else 'not significantly'} "
                f"across {group_col} groups (F={f_stat:.3f}, {len(groups)} groups, n={len(working)})."
            ),
            caveats=["assumes roughly equal variances across groups"],
        )
