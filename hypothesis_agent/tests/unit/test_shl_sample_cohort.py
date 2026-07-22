"""Offline parsing test against the real Book1.xlsx — no network, no LLM.
Skipped if the file isn't present (e.g. a checkout without the sample data)."""

from pathlib import Path

import pytest

from hypothesis_agent.adapters.shl_sample_cohort import (
    ORGANIZATION_ID,
    load_organization_and_landscape,
)

_XLSX_PATH = Path(__file__).parents[3] / "Book1.xlsx"

pytestmark = pytest.mark.skipif(not _XLSX_PATH.exists(), reason="Book1.xlsx not present")


def test_loads_expected_shape():
    profile, landscape = load_organization_and_landscape(_XLSX_PATH)
    assert profile.organization_id == ORGANIZATION_ID == landscape.organization_id
    assert landscape.employee_count_estimate == 378
    assert len(landscape.available_fields) == 153


def test_categories_partition_all_fields():
    _, landscape = load_organization_and_landscape(_XLSX_PATH)
    counts = {
        category: sum(1 for f in landscape.available_fields if f.category == category)
        for category in landscape.categories()
    }
    assert counts == {
        "behavioural_competency": 124,
        "organizational_fit": 27,
        "psychometrics": 2,
    }


def test_coverage_ratios_are_valid_fractions():
    _, landscape = load_organization_and_landscape(_XLSX_PATH)
    for field in landscape.available_fields:
        assert field.coverage_ratio is not None
        assert 0.0 <= field.coverage_ratio <= 1.0


def test_never_exposes_row_level_values():
    """The landscape is schema-only — no candidate IDs or raw scores."""
    _, landscape = load_organization_and_landscape(_XLSX_PATH)
    dumped = landscape.model_dump()
    assert "Candidate_ID" not in str(dumped)
