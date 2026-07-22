"""Exercises the FastAPI app against a temp JSON store (never the real
sample_data/stories.json) by pointing HYPOTHESIS_AGENT__BACKENDS__JSON_STORE_PATH
at a tmp_path before the module-level singletons in server/app.py are built,
then reloading the module. Forces backends.llm/embedding to the offline mock
backends explicitly — a local .env may set backends.llm=litellm for real
server runs, but this test must never make a network call."""

from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("HYPOTHESIS_AGENT__BACKENDS__JSON_STORE_PATH", str(tmp_path / "stories.json"))
    monkeypatch.setenv("HYPOTHESIS_AGENT__BACKENDS__LLM", "mock")
    monkeypatch.setenv("HYPOTHESIS_AGENT__BACKENDS__EMBEDDING", "hash")
    monkeypatch.setenv("HYPOTHESIS_AGENT__SEARCH__MAX_ITERATIONS", "2")
    monkeypatch.setenv("HYPOTHESIS_AGENT__SEARCH__RANDOM_SEED", "7")

    import hypothesis_agent.server.app as app_module

    importlib.reload(app_module)
    return TestClient(app_module.app)


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_stories_starts_empty(client):
    response = client.get("/api/stories")
    assert response.status_code == 200
    assert response.json() == []


def test_generate_appends_a_story_reachable_via_get(client):
    response = client.post("/api/generate", json={"organization_id": "acme-labs"})
    assert response.status_code == 200
    body = response.json()
    assert body["hypothesis_statement"]
    assert body["headline"]

    stories = client.get("/api/stories").json()
    assert len(stories) == 1
    assert stories[0]["reaction"] == "none"
    # The feed shows the catchy headline, not the full statement; the full
    # text is still preserved for the detail page.
    assert stories[0]["title"] == body["headline"]
    assert stories[0]["statement"] == body["hypothesis_statement"]


def test_reaction_round_trip(client):
    generated = client.post("/api/generate", json={"organization_id": "acme-labs"}).json()
    story_id = client.get("/api/stories").json()[0]["id"]

    up = client.post(f"/api/stories/{story_id}/reaction", json={"reaction": "up"})
    assert up.status_code == 200
    assert client.get("/api/stories").json()[0]["reaction"] == "up"

    cleared = client.post(f"/api/stories/{story_id}/reaction", json={"reaction": "none"})
    assert cleared.status_code == 200
    assert client.get("/api/stories").json()[0]["reaction"] == "none"


def test_reaction_on_unknown_story_returns_404(client):
    response = client.post("/api/stories/does-not-exist/reaction", json={"reaction": "up"})
    assert response.status_code == 404
