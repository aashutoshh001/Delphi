from pathlib import Path

import pytest

from hypothesis_agent.adapters.llm.mock_llm_service import MockLLMService
from hypothesis_agent.adapters.repositories.in_memory_employee_repository import (
    InMemoryEmployeeRepository,
)
from insight_pipeline.adapters.dataset_retrieval.default_retriever import DefaultDatasetRetriever
from insight_pipeline.adapters.employee_data.excel_repository import ExcelEmployeeDataRepository
from insight_pipeline.adapters.employee_data.handle_cache import InMemoryDatasetHandleCache
from insight_pipeline.adapters.query_planning.direct_llm_planner import DirectLLMQueryPlanner
from insight_pipeline.agents.data_retrieval.facade import DataRetrievalAgent
from insight_pipeline.contracts.investigation import InvestigationPlan, PopulationSpec, VariableSpec
from insight_pipeline.prompts.registry import default_prompt_registry

_XLSX_PATH = Path(__file__).parents[3] / "Book1.xlsx"

pytestmark = pytest.mark.skipif(not _XLSX_PATH.exists(), reason="Book1.xlsx not present")


async def test_data_retrieval_agent_end_to_end_against_real_cohort():
    from hypothesis_agent.adapters.shl_sample_cohort import load_organization_and_landscape

    profile, landscape = load_organization_and_landscape(_XLSX_PATH)

    employee_repository = InMemoryEmployeeRepository()
    employee_repository.add(landscape)

    cache = InMemoryDatasetHandleCache()
    query_planner = DirectLLMQueryPlanner(MockLLMService(), default_prompt_registry())
    employee_data_repository = ExcelEmployeeDataRepository(_XLSX_PATH, cache)
    retriever = DefaultDatasetRetriever(employee_repository, query_planner, employee_data_repository)
    agent = DataRetrievalAgent(retriever)

    plan = InvestigationPlan(
        hypothesis_package_id="pkg_test",
        organization_id=profile.organization_id,
        variables_required=[
            VariableSpec(name="Leadership", role="independent", expected_type="numeric"),
            VariableSpec(name="Resilience", role="dependent", expected_type="numeric"),
        ],
        target_population=PopulationSpec(description="all assessed candidates"),
    )

    dataset = await agent.run(plan)

    assert dataset.handle.row_count == 378
    assert dataset.investigation_plan_id == plan.id
    df = cache.load(dataset.handle)
    assert len(df) == 378
