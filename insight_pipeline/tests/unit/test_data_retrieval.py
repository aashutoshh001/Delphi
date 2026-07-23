from pathlib import Path

import pytest

from insight_pipeline.adapters.employee_data.excel_repository import ExcelEmployeeDataRepository
from insight_pipeline.adapters.employee_data.handle_cache import InMemoryDatasetHandleCache
from insight_pipeline.contracts.dataset import RetrievalQuery

_XLSX_PATH = Path(__file__).parents[3] / "Book1_standardized.xlsx"

pytestmark = pytest.mark.skipif(not _XLSX_PATH.exists(), reason="Book1_standardized.xlsx not present")


async def test_resolve_returns_handle_with_requested_columns():
    cache = InMemoryDatasetHandleCache()
    repo = ExcelEmployeeDataRepository(_XLSX_PATH, cache)
    query = RetrievalQuery(
        organization_id="shl-sample-cohort",
        requested_fields=["4_personality", "tenure_years", "360.1_self"],
    )
    handle = await repo.resolve(query)
    assert handle.row_count == 402

    df = cache.load(handle)
    assert "4_personality" in df.columns
    assert "tenure_years" in df.columns
    assert "candidate_id" in df.columns
    assert len(df) == 402


async def test_resolve_falls_back_to_full_table_on_no_match():
    cache = InMemoryDatasetHandleCache()
    repo = ExcelEmployeeDataRepository(_XLSX_PATH, cache)
    query = RetrievalQuery(organization_id="shl-sample-cohort", requested_fields=["Nonexistent_Field"])
    handle = await repo.resolve(query)
    df = cache.load(handle)
    assert len(df.columns) > 100  # fell back to (almost) the whole table


async def test_handle_cache_raises_for_unknown_location():
    cache = InMemoryDatasetHandleCache()
    from insight_pipeline.contracts.dataset import DatasetHandle

    with pytest.raises(KeyError):
        cache.load(DatasetHandle(backend="excel", location="does-not-exist", row_count=0))
