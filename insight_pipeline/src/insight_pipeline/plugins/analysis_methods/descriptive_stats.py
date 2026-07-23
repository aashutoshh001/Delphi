"""General grounded descriptive-statistics method — ported from
base-agents-strands' talent_intelligence/tools/nl2sql.py::_build_descriptive_stats
(V2 architecture plan Part 4D angle 7 / Part 2 asset table). Unlike the
fixed four hypothesis-testing methods (correlation/regression/ANOVA/
chi-square), this always runs when at least one grounded column is present
— numeric columns get pandas .describe(), categorical columns get top-N
value counts — giving the report a real, grounded orientation view even
when no pairwise test is applicable."""

from __future__ import annotations

import pandas as pd

from insight_pipeline.adapters.employee_data.handle_cache import InMemoryDatasetHandleCache
from insight_pipeline.contracts.analytics import AnalysisMethodResult
from insight_pipeline.contracts.dataset import DatasetHandle, DatasetMetadata
from insight_pipeline.contracts.investigation import InvestigationPlan
from insight_pipeline.plugins.analysis_methods._column_matching import matched_variables
from insight_pipeline.plugins.analysis_methods.base import AnalysisMethodPlugin

_MAX_CATEGORICAL_VALUES = 5
_MAX_COLUMNS = 8  # cap prompt/report length; the fuller picture lives in the other angle methods


class DescriptiveStatsPlugin(AnalysisMethodPlugin):
    method_name = "descriptive_stats"

    def __init__(self, handle_cache: InMemoryDatasetHandleCache) -> None:
        self._handle_cache = handle_cache

    async def is_applicable(self, plan: InvestigationPlan, metadata: DatasetMetadata) -> bool:
        return bool(plan.variables_required)

    async def run(self, handle: DatasetHandle, plan: InvestigationPlan) -> AnalysisMethodResult:
        df = self._handle_cache.load(handle)
        matched = matched_variables(df, plan.variables_required)[:_MAX_COLUMNS]
        if not matched:
            return AnalysisMethodResult(
                method=self.method_name,
                interpretation_notes="No grounded variables matched the resolved dataset.",
                caveats=["skipped — no matched columns"],
            )

        blocks: list[str] = []
        columns_involved: list[str] = []
        for variable, column in matched:
            columns_involved.append(column)
            series = df[column]
            if variable.expected_type in ("numeric", "ordinal"):
                numeric = pd.to_numeric(series, errors="coerce").dropna()
                if numeric.empty:
                    continue
                blocks.append(
                    f"- {column}: n={len(numeric)}, mean={numeric.mean():.3f}, std={numeric.std():.3f}, "
                    f"min={numeric.min():.3f}, max={numeric.max():.3f}"
                )
            else:
                non_null = series.dropna()
                if non_null.empty:
                    continue
                top = non_null.astype(str).value_counts().head(_MAX_CATEGORICAL_VALUES)
                top_str = ", ".join(f"{val} ({count})" for val, count in top.items())
                blocks.append(f"- {column}: n={len(non_null)}, unique={non_null.nunique()}, top values: {top_str}")

        if not blocks:
            return AnalysisMethodResult(
                method=self.method_name,
                variables_involved=columns_involved,
                interpretation_notes="Matched columns had no non-missing values to summarize.",
                caveats=["all-null matched columns"],
            )

        return AnalysisMethodResult(
            method=self.method_name,
            variables_involved=columns_involved,
            interpretation_notes="Descriptive summary of the grounded variables actually present in the resolved dataset:\n"
            + "\n".join(blocks),
            caveats=["descriptive only — no hypothesis test performed"],
        )
