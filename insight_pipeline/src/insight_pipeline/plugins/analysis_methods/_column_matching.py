"""Best-effort mapping from an LLM-authored VariableSpec.name onto an actual
dataframe column — the Investigation Planner's variable names and the Query
Planner's resolved field names usually agree (the planner sees the exact
available-fields list), but aren't contractually guaranteed to. Shared by
every AnalysisMethodPlugin rather than reimplemented per plugin."""

from __future__ import annotations

import pandas as pd

from insight_pipeline.contracts.investigation import VariableSpec


def match_column(df: pd.DataFrame, variable_name: str) -> str | None:
    if variable_name in df.columns:
        return variable_name
    lowered = {c.lower(): c for c in df.columns}
    return lowered.get(variable_name.lower())


def matched_variables(
    df: pd.DataFrame, variables: list[VariableSpec]
) -> list[tuple[VariableSpec, str]]:
    matched = []
    for variable in variables:
        column = match_column(df, variable.name)
        if column is not None:
            matched.append((variable, column))
    return matched


def numeric_column(df: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(df[column], errors="coerce")
