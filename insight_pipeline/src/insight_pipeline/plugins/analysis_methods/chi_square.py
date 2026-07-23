from __future__ import annotations

import pandas as pd
from scipy import stats

from insight_pipeline.adapters.employee_data.handle_cache import InMemoryDatasetHandleCache
from insight_pipeline.contracts.analytics import AnalysisMethodResult
from insight_pipeline.contracts.dataset import DatasetHandle, DatasetMetadata
from insight_pipeline.contracts.investigation import InvestigationPlan
from insight_pipeline.plugins.analysis_methods._column_matching import matched_variables
from insight_pipeline.plugins.analysis_methods.base import AnalysisMethodPlugin


class ChiSquarePlugin(AnalysisMethodPlugin):
    method_name = "chi_square_independence"

    def __init__(self, handle_cache: InMemoryDatasetHandleCache) -> None:
        self._handle_cache = handle_cache

    def _categorical_pair(self, plan: InvestigationPlan, df) -> tuple | None:
        matched = matched_variables(df, plan.variables_required)
        categorical = [(v, c) for v, c in matched if v.expected_type == "categorical"]
        if len(categorical) < 2:
            return None
        return categorical[0], categorical[1]

    async def is_applicable(self, plan: InvestigationPlan, metadata: DatasetMetadata) -> bool:
        return sum(1 for f in metadata.fields if f.data_type == "categorical") >= 2

    async def run(self, handle: DatasetHandle, plan: InvestigationPlan) -> AnalysisMethodResult:
        df = self._handle_cache.load(handle)
        pair = self._categorical_pair(plan, df)
        if pair is None:
            return AnalysisMethodResult(
                method=self.method_name,
                interpretation_notes="No two matched categorical variables were available.",
                caveats=["skipped — insufficient categorical variables"],
            )
        (var_a, col_a), (var_b, col_b) = pair
        table = pd.crosstab(df[col_a], df[col_b])
        if table.shape[0] < 2 or table.shape[1] < 2:
            return AnalysisMethodResult(
                method=self.method_name,
                variables_involved=[col_a, col_b],
                interpretation_notes=f"{col_a} x {col_b} contingency table has fewer than 2 categories on a side.",
                caveats=["insufficient category variation"],
            )
        chi2, p_value, dof, _expected = stats.chi2_contingency(table)
        return AnalysisMethodResult(
            method=self.method_name,
            variables_involved=[col_a, col_b],
            statistic=round(float(chi2), 4),
            p_value=round(float(p_value), 6),
            interpretation_notes=(
                f"{col_a} and {col_b} are {'not independent' if p_value < 0.05 else 'not distinguishably related'} "
                f"(chi2={chi2:.3f}, dof={dof}, n={int(table.values.sum())})."
            ),
            caveats=["sensitive to small expected cell counts"],
        )
