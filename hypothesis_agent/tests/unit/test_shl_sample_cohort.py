"""Offline parsing test against the real Book1_standardized.xlsx — no
network, no LLM. Skipped if the file isn't present (e.g. a checkout without
the sample data)."""

from pathlib import Path

import pytest

from hypothesis_agent.adapters.shl_sample_cohort import (
    ORGANIZATION_ID,
    load_organization_and_landscape,
)

_XLSX_PATH = Path(__file__).parents[3] / "Book1_standardized.xlsx"

pytestmark = pytest.mark.skipif(not _XLSX_PATH.exists(), reason="Book1_standardized.xlsx not present")


def test_loads_expected_shape():
    profile, landscape = load_organization_and_landscape(_XLSX_PATH)
    assert profile.organization_id == ORGANIZATION_ID == landscape.organization_id
    assert landscape.employee_count_estimate == 402
    assert len(landscape.available_fields) == 234  # 235 columns - candidate_id


def test_categories_partition_all_fields():
    _, landscape = load_organization_and_landscape(_XLSX_PATH)
    counts = {
        category: sum(1 for f in landscape.available_fields if f.category == category)
        for category in landscape.categories()
    }
    assert counts == {
        "opq_domain": 8,
        "opq_facet": 20,
        "gsa_skill_item": 96,
        "leader_challenge_fit": 27,
        "motivation_item": 36,
        "enterprise_leadership_domain": 3,
        "hipo_composite": 2,
        "rater_360": 40,
        "outcome": 2,
    }
    assert "other" not in counts  # every real column classifies — nothing falls through


def test_coverage_ratios_are_valid_fractions():
    _, landscape = load_organization_and_landscape(_XLSX_PATH)
    for field in landscape.available_fields:
        assert field.coverage_ratio is not None
        assert 0.0 <= field.coverage_ratio <= 1.0


def test_never_exposes_row_level_values():
    """The landscape is schema-only — no candidate IDs or raw scores."""
    _, landscape = load_organization_and_landscape(_XLSX_PATH)
    dumped = landscape.model_dump()
    assert "candidate_id" not in str(dumped)


def test_default_path_is_repo_root_anchored():
    """No explicit path -> resolves to Delphi/Book1_standardized.xlsx
    regardless of the caller's cwd (same anchoring discipline as
    config/settings.py — this file previously depended on the process's cwd,
    which caused real production incidents earlier in this project)."""
    profile, landscape = load_organization_and_landscape()
    assert profile.organization_id == ORGANIZATION_ID
    assert landscape.employee_count_estimate == 402
