from pathlib import Path

import pytest

from hypothesis_agent.adapters.repositories.in_memory_employee_repository import (
    InMemoryEmployeeRepository,
)
from insight_pipeline.adapters.dataset_retrieval.default_retriever import DefaultDatasetRetriever
from insight_pipeline.adapters.employee_data.excel_repository import ExcelEmployeeDataRepository
from insight_pipeline.adapters.employee_data.handle_cache import InMemoryDatasetHandleCache
from insight_pipeline.adapters.query_planning.grounded_planner import GroundedQueryPlanner
from insight_pipeline.agents.data_retrieval.facade import DataRetrievalAgent
from insight_pipeline.contracts.investigation import InvestigationPlan, PopulationSpec, VariableSpec

_XLSX_PATH = Path(__file__).parents[3] / "Book1_standardized.xlsx"

pytestmark = pytest.mark.skipif(not _XLSX_PATH.exists(), reason="Book1_standardized.xlsx not present")


async def test_data_retrieval_agent_end_to_end_against_real_cohort():
    from hypothesis_agent.adapters.shl_sample_cohort import load_organization_and_landscape

    profile, landscape = load_organization_and_landscape(_XLSX_PATH)

    employee_repository = InMemoryEmployeeRepository()
    employee_repository.add(landscape)

    cache = InMemoryDatasetHandleCache()
    query_planner = GroundedQueryPlanner()  # 0 LLM calls — variables are already grounded, real columns
    employee_data_repository = ExcelEmployeeDataRepository(_XLSX_PATH, cache)
    retriever = DefaultDatasetRetriever(employee_repository, query_planner, employee_data_repository)
    agent = DataRetrievalAgent(retriever)

    plan = InvestigationPlan(
        hypothesis_package_id="pkg_test",
        organization_id=profile.organization_id,
        variables_required=[
            VariableSpec(name="4_personality", role="independent", expected_type="numeric"),
            VariableSpec(name="tenure_years", role="dependent", expected_type="numeric"),
        ],
        target_population=PopulationSpec(description="all assessed candidates"),
    )

    dataset = await agent.run(plan)

    assert dataset.handle.row_count == 402
    assert dataset.investigation_plan_id == plan.id
    df = cache.load(dataset.handle)
    assert len(df) == 402
    assert "4_personality" in df.columns
    assert "tenure_years" in df.columns
