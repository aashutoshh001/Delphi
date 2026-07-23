"""The one place per figure that touches the raw dataset — see
docs/PLATFORM_ARCHITECTURE.md §14. Aggregates a DatasetHandle down to small,
chart-ready ResolvedChartData. Handles the visualization types the shipped
PlottingEngine adapters actually support (§23 phase 9: bar, scatter,
heatmap/correlation-matrix, histogram, boxplot — the rest of the catalog in
§14 is future work, each addition touching only this resolver + a renderer,
never VisualizationSpec or the Visualization Planner)."""

from __future__ import annotations

import pandas as pd

from insight_pipeline.adapters.employee_data.handle_cache import InMemoryDatasetHandleCache
from insight_pipeline.contracts.dataset import DatasetHandle
from insight_pipeline.contracts.visualization import ResolvedChartData, VisualizationSpec
from insight_pipeline.ports.chart_data_resolver import ChartDataResolver

_CORRELATION_TYPES = {"heatmap", "correlation_matrix"}
_BAR_TYPES = {"bar", "grouped_bar", "bar_chart"}
_SCATTER_TYPES = {"scatter", "scatter_plot"}
_HISTOGRAM_TYPES = {"histogram", "distribution"}
_BOXPLOT_TYPES = {"boxplot", "box_plot"}


class DefaultChartDataResolver(ChartDataResolver):
    def __init__(self, handle_cache: InMemoryDatasetHandleCache) -> None:
        self._handle_cache = handle_cache

    async def resolve(self, spec: VisualizationSpec, handle: DatasetHandle) -> ResolvedChartData:
        df = self._handle_cache.load(handle)
        columns = [c for c in spec.data_requirements if c in df.columns] or [
            c for c in spec.variables if c in df.columns
        ]

        if spec.visualization_type in _CORRELATION_TYPES:
            return self._correlation_matrix(df, columns)
        if spec.visualization_type in _SCATTER_TYPES and len(columns) >= 2:
            return self._scatter(df, columns[0], columns[1])
        if spec.visualization_type in _HISTOGRAM_TYPES and columns:
            return self._histogram(df, columns[0])
        if spec.visualization_type in _BOXPLOT_TYPES and len(columns) >= 2:
            return self._boxplot(df, columns[0], columns[1])
        if columns:
            return self._bar(df, columns[0], columns[1] if len(columns) > 1 else None)
        return ResolvedChartData()

    def _correlation_matrix(self, df: pd.DataFrame, columns: list[str]) -> ResolvedChartData:
        numeric = df[columns].apply(pd.to_numeric, errors="coerce")
        corr = numeric.corr(numeric_only=True).fillna(0.0)
        return ResolvedChartData(
            matrix_labels=list(corr.columns),
            matrix=[[round(float(v), 4) for v in row] for row in corr.values],
        )

    def _scatter(self, df: pd.DataFrame, x_col: str, y_col: str) -> ResolvedChartData:
        xs = pd.to_numeric(df[x_col], errors="coerce")
        ys = pd.to_numeric(df[y_col], errors="coerce")
        points = [(float(x), float(y)) for x, y in zip(xs, ys) if x == x and y == y]
        return ResolvedChartData(categories=[x_col, y_col], raw_points=points)

    def _histogram(self, df: pd.DataFrame, column: str) -> ResolvedChartData:
        values = pd.to_numeric(df[column], errors="coerce").dropna()
        counts, edges = _histogram_bins(values.tolist(), bins=10)
        labels = [f"{edges[i]:.1f}-{edges[i + 1]:.1f}" for i in range(len(edges) - 1)]
        return ResolvedChartData(categories=labels, series={column: counts})

    def _boxplot(self, df: pd.DataFrame, group_col: str, value_col: str) -> ResolvedChartData:
        values = pd.to_numeric(df[value_col], errors="coerce")
        working = df[[group_col]].copy()
        working["__value__"] = values
        working = working.dropna()
        series: dict[str, list[float]] = {}
        for group_name, group_df in working.groupby(group_col):
            series[str(group_name)] = [round(float(v), 4) for v in group_df["__value__"].tolist()]
        return ResolvedChartData(categories=list(series.keys()), series=series)

    def _bar(self, df: pd.DataFrame, group_col: str, value_col: str | None) -> ResolvedChartData:
        if value_col is None:
            counts = df[group_col].value_counts()
            return ResolvedChartData(
                categories=[str(c) for c in counts.index],
                series={"count": [float(v) for v in counts.values]},
            )
        values = pd.to_numeric(df[value_col], errors="coerce")
        if values.notna().any():
            working = df[[group_col]].copy()
            working["__value__"] = values
            working = working.dropna()
            means = working.groupby(group_col)["__value__"].mean()
            return ResolvedChartData(
                categories=[str(c) for c in means.index],
                series={value_col: [round(float(v), 4) for v in means.values]},
            )
        # value_col isn't numeric (e.g. two categorical variables, as chi-square
        # produces) — a mean-of-nothing would silently render empty, so fall
        # back to grouped counts (a crosstab) instead.
        table = pd.crosstab(df[group_col], df[value_col])
        return ResolvedChartData(
            categories=[str(c) for c in table.index],
            series={str(col): [float(v) for v in table[col]] for col in table.columns},
        )


def _histogram_bins(values: list[float], bins: int) -> tuple[list[float], list[float]]:
    if not values:
        return [], [0.0, 1.0]
    lo, hi = min(values), max(values)
    if lo == hi:
        hi = lo + 1.0
    width = (hi - lo) / bins
    edges = [lo + i * width for i in range(bins + 1)]
    counts = [0.0] * bins
    for value in values:
        index = min(int((value - lo) / width), bins - 1)
        counts[index] += 1
    return counts, edges
