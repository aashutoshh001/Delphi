"""Today: Excel. Tomorrow: SQL/Snowflake/HRIS — same EmployeeDataRepository
port, only this file changes. Reuses the same Book1_standardized.xlsx sample
cohort the Hypothesis Agent's landscape adapter reads, but this one actually
returns data (scoped to what an InvestigationPlan asked for), never dumped
into a contract — the resulting DataFrame goes straight into the handle
cache."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from insight_pipeline.adapters.employee_data.handle_cache import InMemoryDatasetHandleCache
from insight_pipeline.contracts.dataset import DatasetHandle, RetrievalQuery
from insight_pipeline.logging_setup import get_logger
from insight_pipeline.ports.employee_data_repository import EmployeeDataRepository

logger = get_logger("adapters.employee_data.excel")


class ExcelEmployeeDataRepository(EmployeeDataRepository):
    def __init__(self, xlsx_path: Path | str, handle_cache: InMemoryDatasetHandleCache) -> None:
        self._xlsx_path = Path(xlsx_path)
        self._handle_cache = handle_cache
        self._raw: pd.DataFrame | None = None

    def _load_raw(self) -> pd.DataFrame:
        if self._raw is None:
            self._raw = pd.read_excel(self._xlsx_path)
        return self._raw

    async def resolve(self, query: RetrievalQuery) -> DatasetHandle:
        df = self._load_raw()
        requested = [c for c in query.requested_fields if c in df.columns]
        if not requested:
            logger.warning(
                "none of the requested fields matched known columns — returning full table",
                extra={"extra_fields": {"requested": query.requested_fields}},
            )
            requested = [c for c in df.columns if c != "candidate_id"]
        id_col = ["candidate_id"] if "candidate_id" in df.columns else []
        selected = df[id_col + [c for c in requested if c not in id_col]].copy()

        # Filters/segmentation from InvestigationPlan are free-text (LLM-authored
        # natural language), not a structured expression — deliberately not
        # mechanically applied here (no eval() over untrusted LLM output).
        # They're preserved as metadata for now; real filter application is
        # production-hardening work (docs/PLATFORM_ARCHITECTURE.md §23 phase 12).
        handle = self._handle_cache.store(selected, backend="excel")
        logger.info(
            "resolved dataset",
            extra={"extra_fields": {"rows": handle.row_count, "columns": len(selected.columns)}},
        )
        return handle
