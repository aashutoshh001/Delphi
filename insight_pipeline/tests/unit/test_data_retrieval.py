from pathlib import Path

import pytest

from insight_pipeline.adapters.employee_data.excel_repository import ExcelEmployeeDataRepository
from insight_pipeline.adapters.employee_data.handle_cache import InMemoryDatasetHandleCache
from insight_pipeline.contracts.dataset import RetrievalQuery

_XLSX_PATH = Path(__file__).parents[3] / "Book1.xlsx"

pytestmark = pytest.mark.skipif(not _XLSX_PATH.exists(), reason="Book1.xlsx not present")


async def test_resolve_returns_handle_with_requested_columns():
    cache = InMemoryDatasetHandleCache()
    repo = ExcelEmployeeDataRepository(_XLSX_PATH, cache)
    query = RetrievalQuery(
        organization_id="shl-sample-cohort",
        requested_fields=["Decision_Making", "Leadership", "Resilience"],
    )
    handle = await repo.resolve(query)
    assert handle.row_count == 378

    df = cache.load(handle)
    assert "Decision_Making" in df.columns
    assert "Leadership" in df.columns
    assert "Candidate_ID" in df.columns
    assert len(df) == 378


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
