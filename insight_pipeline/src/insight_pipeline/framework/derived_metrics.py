"""Composable primitives + official-style derived metrics — the mechanism
that enforces "grounding is atomic, not composite" (V2 architecture plan,
Part 3): every function here takes real column names and validates them
against the DataFrame it's given *before* computing anything. An invented
column name raises immediately; it can never silently produce a fabricated
series that later gets treated as data.

Two tiers, per the plan:

- Composable primitives (`gap`, `ratio`, `z_score`, `banded`,
  `composite_index`) — generic building blocks an analysis method or a
  grounding decision may combine freely, always over real columns.
- `quadrant_divergence` — the flagship two-dimension divergence analysis
  (any two grounded dimensions -> quadrant scatter + gap statistics). Drives
  the HiPo scatter, an Invest/Leverage-style fit-vs-experience view, and the
  360 self-vs-manager (or any rater pair) blind-spot analysis alike."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import pandas as pd
from pydantic import BaseModel, Field


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(
            f"Refusing to compute a derived metric over non-existent column(s) {missing} — "
            "every input to a derived metric must be a real column present in the resolved "
            "dataset (see framework/derived_metrics.py)."
        )


def gap(df: pd.DataFrame, col_a: str, col_b: str) -> pd.Series:
    """col_a - col_b. The self-vs-observed / performance-vs-360 divergence
    primitive — e.g. gap(df, '360.3_self', '360.3_manager')."""
    _require_columns(df, [col_a, col_b])
    return df[col_a] - df[col_b]


def ratio(df: pd.DataFrame, col_a: str, col_b: str) -> pd.Series:
    _require_columns(df, [col_a, col_b])
    denom = df[col_b].replace(0, pd.NA)
    return df[col_a] / denom


def z_score(df: pd.DataFrame, col: str) -> pd.Series:
    _require_columns(df, [col])
    series = df[col]
    std = series.std()
    if not std or pd.isna(std):
        return pd.Series(0.0, index=series.index)
    return (series - series.mean()) / std


def banded(df: pd.DataFrame, col: str, thresholds: list[tuple[str, float]]) -> pd.Series:
    """thresholds: ascending [(label, upper_bound_inclusive), ...], last
    label applies to anything above the final bound. E.g.
    banded(df, 'x', [('Low', 2.5), ('Medium', 3.5), ('High', float('inf'))])."""
    _require_columns(df, [col])
    series = df[col]

    def _band(value: float) -> str | None:
        if pd.isna(value):
            return None
        for label, upper in thresholds:
            if value <= upper:
                return label
        return thresholds[-1][0]

    return series.apply(_band)


def composite_index(df: pd.DataFrame, columns: list[str], weights: list[float] | None = None) -> pd.Series:
    """Weighted mean of z-scored real columns — comparable even when inputs
    are on different scales (e.g. a 0-5 skill item blended with a 0-1
    percentile-fit column)."""
    _require_columns(df, columns)
    if weights is None:
        weights = [1.0] * len(columns)
    if len(weights) != len(columns):
        raise ValueError("composite_index: weights must match columns 1:1")
    zscored = pd.concat([z_score(df, c) for c in columns], axis=1)
    total_weight = sum(weights)
    return (zscored.mul(weights, axis=1).sum(axis=1)) / total_weight


def interaction(df: pd.DataFrame, col_a: str, col_b: str) -> pd.Series:
    _require_columns(df, [col_a, col_b])
    return df[col_a] * df[col_b]


class DerivedMetric(BaseModel):
    """An 'official' SHL-style derived metric — a named, documented
    computation over real inputs, distinct from an ad-hoc composite in that
    it has a fixed formula and a business-recognizable name (e.g. a domain
    rollup average, an HiPo band). Still: `inputs` must be real columns,
    checked the same way as the primitives above."""

    name: str
    inputs: list[str]
    description: str


def gsa_domain_rollup(df: pd.DataFrame, domain_columns: list[str]) -> pd.Series:
    """Mean of every GSA skill item under one Great-8 domain — the same
    rollup relationship base-agents-strands documents between its 96
    sub-competency columns and its 8 Great-8 aggregate columns, computed
    here because this sheet doesn't carry a separate pre-aggregated GSA
    domain column the way it does for OPQ (whose {1-8}_personality columns
    already ARE the Great-8 rollup)."""
    _require_columns(df, domain_columns)
    return df[domain_columns].mean(axis=1)


def mq_facet_rollup(df: pd.DataFrame, facet_columns: list[str]) -> pd.Series:
    """Mean of the raw Motivation Questionnaire items sharing one lettered
    facet group (e.g. all MQ.E.*_raw columns)."""
    _require_columns(df, facet_columns)
    return df[facet_columns].mean(axis=1)


def rater_consensus_spread(df: pd.DataFrame, rater_columns: list[str]) -> pd.Series:
    """Standard deviation across the 5 rater perspectives for one 360
    dimension — low spread = raters agree; high spread = a genuine
    perception gap worth surfacing on its own, independent of any single
    gap() pair."""
    _require_columns(df, rater_columns)
    return df[rater_columns].std(axis=1)


@dataclass
class DivergenceResult:
    """Output of quadrant_divergence(): per-row quadrant assignment plus
    population-level divergence statistics, everything traceable back to the
    two real input columns."""

    x_column: str
    y_column: str
    x_threshold: float
    y_threshold: float
    quadrants: pd.Series  # per-row quadrant label
    quadrant_counts: dict[str, int] = field(default_factory=dict)
    gap_mean: float = 0.0
    gap_std: float = 0.0
    off_diagonal_ratio: float = 0.0  # fraction of rows materially off the x=y diagonal


def quadrant_divergence(
    df: pd.DataFrame,
    x_column: str,
    y_column: str,
    x_threshold: float,
    y_threshold: float,
    quadrant_labels: tuple[str, str, str, str] = ("High-High", "High-Low", "Low-High", "Low-Low"),
    diagonal_tolerance: float | None = None,
) -> DivergenceResult:
    """The flagship generalized quadrant-divergence analysis (V2 architecture
    plan Part 4D angle 4 / Part 4F chart): any two real, same-scale-ish
    dimensions -> four quadrants by threshold, plus how far the population
    sits off the x=y diagonal (the "systematic gap" signal — e.g. a whole
    team rating itself higher than managers rate them).

    quadrant_labels = (x>=thr & y>=thr, x>=thr & y<thr, x<thr & y>=thr, x<thr & y<thr).
    """
    _require_columns(df, [x_column, y_column])
    x = df[x_column]
    y = df[y_column]

    def _label(xv: float, yv: float) -> str | None:
        if pd.isna(xv) or pd.isna(yv):
            return None
        if xv >= x_threshold and yv >= y_threshold:
            return quadrant_labels[0]
        if xv >= x_threshold and yv < y_threshold:
            return quadrant_labels[1]
        if xv < x_threshold and yv >= y_threshold:
            return quadrant_labels[2]
        return quadrant_labels[3]

    quadrants = pd.Series([_label(xv, yv) for xv, yv in zip(x, y)], index=df.index)
    counts = quadrants.value_counts(dropna=True).to_dict()

    diff = (x - y).dropna()
    gap_mean = float(diff.mean()) if not diff.empty else 0.0
    gap_std = float(diff.std()) if len(diff) > 1 else 0.0

    if diagonal_tolerance is None:
        span = max(float(x.max() - x.min()) if x.notna().any() else 0.0, 1e-9)
        diagonal_tolerance = span * 0.1
    off_diagonal = diff.abs() > diagonal_tolerance
    off_diagonal_ratio = float(off_diagonal.mean()) if not diff.empty else 0.0

    return DivergenceResult(
        x_column=x_column,
        y_column=y_column,
        x_threshold=x_threshold,
        y_threshold=y_threshold,
        quadrants=quadrants,
        quadrant_counts={str(k): int(v) for k, v in counts.items()},
        gap_mean=gap_mean,
        gap_std=gap_std,
        off_diagonal_ratio=off_diagonal_ratio,
    )
