"""In-process cache resolving a DatasetHandle to an actual pandas DataFrame.

Deliberately NOT a port — it returns a dataframe, which contracts/ports must
never do (docs/PLATFORM_ARCHITECTURE.md §2). Only adapter-internal code
(EmployeeDataRepository writing to it, AnalysisMethodPlugins and
ChartDataResolver reading from it) ever touches this module. A single
process-wide instance is enough for the monorepo phase; §24 of the
architecture doc flags swapping this for a real object store/temp-table
once agents split into separate services."""

from __future__ import annotations

import uuid

import pandas as pd

from insight_pipeline.contracts.dataset import DatasetHandle


class InMemoryDatasetHandleCache:
    def __init__(self) -> None:
        self._tables: dict[str, pd.DataFrame] = {}

    def store(self, df: pd.DataFrame, backend: str = "excel") -> DatasetHandle:
        location = uuid.uuid4().hex[:16]
        self._tables[location] = df
        return DatasetHandle(
            backend=backend, location=location, row_count=len(df), columns=list(df.columns)
        )

    def load(self, handle: DatasetHandle) -> pd.DataFrame:
        try:
            return self._tables[handle.location]
        except KeyError as exc:
            raise KeyError(
                f"no cached dataframe for handle location '{handle.location}' "
                "(cache cleared, or handle resolved in a different process)"
            ) from exc


_default_cache = InMemoryDatasetHandleCache()


def default_handle_cache() -> InMemoryDatasetHandleCache:
    return _default_cache
