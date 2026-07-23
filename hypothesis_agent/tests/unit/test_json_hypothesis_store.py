import json

import pytest

from hypothesis_agent.adapters.embeddings.hash_embedding_service import HashEmbeddingService
from hypothesis_agent.adapters.repositories.json_hypothesis_store import (
    JsonHypothesisStore,
)
from hypothesis_agent.contracts.hypothesis import EvaluationScorecard
from hypothesis_agent.contracts.memory import FeedbackRecord, HistoricalHypothesisRecord


@pytest.fixture
def store(tmp_path):
    path = tmp_path / "stories.json"
    return JsonHypothesisStore(path, HashEmbeddingService(dimensions=32), render_detail_pages=False)


def _record(**overrides) -> HistoricalHypothesisRecord:
    defaults = dict(
        organization_id="org-1",
        statement="High performers show elevated burnout.",
        mechanism="Sustained overperformance without recovery time erodes resilience.",
        lens="burnout_resilience",
        target_constructs=["burnout", "performance"],
        scorecard=EvaluationScorecard(business_value=0.8, composite=0.7),
    )
    defaults.update(overrides)
    return HistoricalHypothesisRecord(**defaults)


async def test_save_then_list_recent_round_trips(store):
    record = _record()
    await store.save(record)

    recent = await store.list_recent("org-1")
    assert len(recent) == 1
    assert recent[0].statement == record.statement
    assert recent[0].lens == "burnout_resilience"


async def test_saved_entry_defaults_reaction_to_none(store):
    await store.save(_record())
    raw = await store.list_raw()
    assert raw[0]["reaction"] == "none"


async def test_search_similar_finds_near_duplicate_text(store):
    await store.save(_record(statement="High performers show elevated burnout."))
    embedding = await store._embedding_service.embed("High performers show elevated burnout.")
    results = await store.search_similar(embedding, "org-1", top_k=3)
    assert results
    assert results[0].embedding is not None


async def test_search_similar_filters_by_organization(store):
    await store.save(_record(organization_id="org-1"))
    embedding = await store._embedding_service.embed("High performers show elevated burnout.")
    results = await store.search_similar(embedding, "org-2", top_k=3)
    assert results == []


async def test_set_reaction_updates_existing_entry(store):
    await store.save(_record())
    raw = await store.list_raw()
    hyp_id = raw[0]["id"]

    found = await store.set_reaction(hyp_id, "up")
    assert found is True

    raw = await store.list_raw()
    assert raw[0]["reaction"] == "up"


async def test_set_reaction_returns_false_for_unknown_id(store):
    found = await store.set_reaction("does-not-exist", "up")
    assert found is False


async def test_set_reaction_rejects_invalid_value(store):
    await store.save(_record())
    raw = await store.list_raw()
    with pytest.raises(ValueError):
        await store.set_reaction(raw[0]["id"], "maybe")


async def test_record_feedback_raises_for_unknown_hypothesis(store):
    with pytest.raises(KeyError):
        await store.record_feedback(FeedbackRecord(hypothesis_id="nope", signal="up"))


async def test_get_lens_feedback_counts_aggregates_by_lens(store):
    await store.save(_record(lens="burnout_resilience"))
    await store.save(_record(lens="burnout_resilience", statement="A second, different statement."))
    await store.save(_record(lens="skill_concentration", statement="A third, unrelated statement."))
    raw = await store.list_raw()

    await store.set_reaction(raw[0]["id"], "up")
    await store.set_reaction(raw[1]["id"], "down")
    await store.set_reaction(raw[2]["id"], "up")

    counts = await store.get_lens_feedback_counts("org-1")
    assert counts["burnout_resilience"].up_count == 1
    assert counts["burnout_resilience"].down_count == 1
    assert counts["skill_concentration"].up_count == 1


async def test_reading_missing_file_returns_empty_list(tmp_path):
    store = JsonHypothesisStore(tmp_path / "missing.json", HashEmbeddingService())
    assert await store.list_raw() == []
    assert await store.list_recent(None) == []


async def test_file_on_disk_is_valid_json_after_save(store):
    await store.save(_record())
    raw_text = store._path.read_text()
    parsed = json.loads(raw_text)
    assert len(parsed) == 1
    assert "readmoreURL" in parsed[0]


async def test_saved_entry_gets_a_card_image_url_and_file(tmp_path):
    path = tmp_path / "stories.json"
    store = JsonHypothesisStore(path, HashEmbeddingService(dimensions=32), render_detail_pages=False)
    await store.save(_record())

    raw = await store.list_raw()
    image_url = raw[0]["imageURL"]
    assert image_url.startswith("sample_data/card_images/")
    assert image_url.endswith(f"{raw[0]['id']}.svg")

    image_path = path.parent / "card_images" / f"{raw[0]['id']}.svg"
    assert image_path.exists()
    assert "<svg" in image_path.read_text()


async def test_render_card_images_false_leaves_image_url_empty(tmp_path):
    path = tmp_path / "stories.json"
    store = JsonHypothesisStore(
        path, HashEmbeddingService(dimensions=32), render_detail_pages=False, render_card_images=False
    )
    await store.save(_record())

    raw = await store.list_raw()
    assert raw[0]["imageURL"] == ""
    assert not (path.parent / "card_images").exists()
