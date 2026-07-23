"""WorkdayEmployeeRepository — offline landscape door. The live probe is never
exercised here (probe_workday defaults False), so these stay offline/deterministic."""

import pytest

from hypothesis_agent.adapters.repositories.workday_employee_repository import (
    WorkdayEmployeeRepository,
)
from hypothesis_agent.config.settings import AgentConfig
from hypothesis_agent.di.container import build_dependencies


async def test_offline_landscape_advertises_workday_and_shl_fields():
    repo = WorkdayEmployeeRepository()  # offline by default
    landscape = await repo.get_data_landscape("shl-cohort")

    assert landscape.organization_id == "shl-cohort"
    assert landscape.employee_count_estimate == 378  # live-confirmed tenant count
    names = {f.name for f in landscape.available_fields}
    # both data sources are advertised
    assert {"compensation_annual", "tenure_years", "performance_rating"} <= names  # Workday HRIS
    assert {"ucf_skill_scores", "hipo_scores", "leadership_challenges"} <= names   # SHL assessments
    assert "Workday HRIS" in landscape.notes


async def test_categories_light_up_relevant_lenses():
    repo = WorkdayEmployeeRepository()
    landscape = await repo.get_data_landscape("shl-cohort")
    cats = landscape.categories()
    # e.g. compensation_fairness / leadership lenses need these
    assert {"compensation", "tenure", "performance", "leadership"} <= cats


async def test_offline_probe_disabled_makes_no_network_call(monkeypatch):
    # With probe False (default), _probe_workday must never be reached.
    repo = WorkdayEmployeeRepository(probe_workday=False)

    def _boom(*a, **k):
        raise AssertionError("network probe should not run when probe_workday=False")

    monkeypatch.setattr(repo, "_probe_workday", _boom)
    landscape = await repo.get_data_landscape("shl-cohort")
    assert landscape.employee_count_estimate == 378


def test_container_wires_workday_backend():
    config = AgentConfig.load()
    config.backends.employee_repository = "workday"
    deps = build_dependencies(config)
    assert isinstance(deps.employee_repository, WorkdayEmployeeRepository)
