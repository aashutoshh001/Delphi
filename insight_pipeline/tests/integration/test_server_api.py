"""Exercises the FastAPI app against a temp insight store (never the real
sample_data/insights.json) and the real Book1.xlsx (read-only), offline via
MockLLMService."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_XLSX_PATH = Path(__file__).parents[3] / "Book1.xlsx"

pytestmark = pytest.mark.skipif(not _XLSX_PATH.exists(), reason="Book1.xlsx not present")


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("HYPOTHESIS_AGENT__BACKENDS__LLM", "mock")
    monkeypatch.setenv("HYPOTHESIS_AGENT__BACKENDS__EMBEDDING", "hash")
    monkeypatch.setenv("HYPOTHESIS_AGENT__SEARCH__RANDOM_SEED", "7")
    monkeypatch.setenv("HYPOTHESIS_AGENT__SEARCH__MAX_ITERATIONS", "2")
    monkeypatch.setenv("INSIGHT_PIPELINE__BACKENDS__EXCEL_PATH", str(_XLSX_PATH))
    monkeypatch.setenv(
        "INSIGHT_PIPELINE__BACKENDS__INSIGHT_STORE_PATH", str(tmp_path / "insights.json")
    )
    monkeypatch.setenv(
        "INSIGHT_PIPELINE__VISUALIZATION__FIGURE_OUTPUT_DIR", str(tmp_path / "figures")
    )

    import insight_pipeline.server.app as app_module

    importlib.reload(app_module)
    return TestClient(app_module.app)


def _hypothesis_package_payload() -> dict:
    from hypothesis_agent.contracts.hypothesis import (
        CritiqueResult,
        EvaluationScorecard,
        HypothesisPackage,
        SearchStatistics,
    )

    package = HypothesisPackage(
        organization_id="shl-sample-cohort",
        hypothesis_statement="High performers show elevated burnout under ambiguous authority.",
        mechanism_explanation="Execution capability without decision rights concentrates load.",
        business_lens="skill_concentration",
        target_constructs=["burnout", "decision_rights"],
        scorecard=EvaluationScorecard(composite=0.7),
        critique=CritiqueResult(),
        search_stats=SearchStatistics(),
    )
    return {"hypothesis_package": package.model_dump(mode="json")}


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_insights_starts_empty(client):
    response = client.get("/api/insights")
    assert response.status_code == 200
    assert response.json() == []


def test_investigate_produces_a_retrievable_insight(client):
    response = client.post("/api/investigate", json=_hypothesis_package_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["insight_package_id"]

    listing = client.get("/api/insights").json()
    assert len(listing) == 1
    assert listing[0]["id"] == body["insight_package_id"]

    detail = client.get(f"/api/insights/{body['insight_package_id']}")
    assert detail.status_code == 200
    assert detail.json()["id"] == body["insight_package_id"]


def test_get_unknown_insight_returns_404(client):
    response = client.get("/api/insights/does-not-exist")
    assert response.status_code == 404
