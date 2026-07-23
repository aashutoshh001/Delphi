"""Tests the SHL Metric Framework against the real Book1_standardized.xlsx
so classification/derived-metric correctness is checked against real data,
not a synthetic fixture that might not match the actual coding scheme."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from insight_pipeline.framework.derived_metrics import (
    banded,
    composite_index,
    gap,
    gsa_domain_rollup,
    quadrant_divergence,
    ratio,
    z_score,
)
from insight_pipeline.framework.outcome_detection import classify_columns
from insight_pipeline.framework.registry import FrameworkRegistry
from insight_pipeline.framework.schema import MetricFamily, classify_column_name

_XLSX_PATH = Path(__file__).parents[3] / "Book1_standardized.xlsx"
pytestmark = pytest.mark.skipif(not _XLSX_PATH.exists(), reason="Book1_standardized.xlsx not present")


@pytest.fixture(scope="module")
def real_df() -> pd.DataFrame:
    return pd.read_excel(_XLSX_PATH)


@pytest.fixture(scope="module")
def registry(real_df: pd.DataFrame) -> FrameworkRegistry:
    return FrameworkRegistry.from_dataframe(real_df)


# -- schema.py: pure name classification --------------------------------


@pytest.mark.parametrize(
    "name,expected_family,expected_hierarchy",
    [
        ("4_personality", MetricFamily.OPQ_DOMAIN, {"domain": "4"}),
        ("1.1_personality", MetricFamily.OPQ_FACET, {"domain": "1", "sub": "1"}),
        ("1.1.a_skill", MetricFamily.GSA_SKILL_ITEM, {"domain": "1", "group": "1", "item": "a"}),
        ("LC.2.c_pct", MetricFamily.LEADER_CHALLENGE_FIT, {"category": "2", "item": "c"}),
        ("MQ.E.3_raw", MetricFamily.MOTIVATION_ITEM, {"facet": "E", "n": "3", "variant": "raw"}),
        ("EL.2_sten", MetricFamily.ENTERPRISE_LEADERSHIP_DOMAIN, {"index": "2"}),
        ("HIPO.1_bucket", MetricFamily.HIPO_COMPOSITE, {"index": "1"}),
        ("360.5_manager", MetricFamily.RATER_360, {"dimension": "5", "rater": "manager"}),
        ("candidate_id", MetricFamily.IDENTITY, {}),
        ("totally_made_up_column", MetricFamily.UNKNOWN, {}),
    ],
)
def test_classify_column_name(name, expected_family, expected_hierarchy):
    family, hierarchy = classify_column_name(name)
    assert family == expected_family
    assert hierarchy == expected_hierarchy


# -- outcome_detection.py + registry.py against the real file -----------


def test_every_real_column_classifies(real_df: pd.DataFrame):
    classification = classify_columns(real_df)
    assert set(classification.definitions.keys()) == set(real_df.columns)
    # confirmed counts from direct inspection (see architecture plan Part 5)
    assert len(classification.identity_columns) == 1
    assert "tenure_years" in classification.outcome_columns
    assert "compensation_annual_usd" in classification.outcome_columns
    # nothing should be UNKNOWN for this known file — every column matches
    # either an assessment pattern, an outcome pattern, or identity
    assert classification.unknown_columns == []


def test_registry_family_counts(registry: FrameworkRegistry):
    assert len(registry.columns_in_family(MetricFamily.OPQ_DOMAIN)) == 8
    assert len(registry.columns_in_family(MetricFamily.OPQ_FACET)) == 20  # 28 total personality cols - 8 domain rollups
    assert len(registry.columns_in_family(MetricFamily.GSA_SKILL_ITEM)) == 96
    assert len(registry.columns_in_family(MetricFamily.LEADER_CHALLENGE_FIT)) == 27
    assert len(registry.columns_in_family(MetricFamily.MOTIVATION_ITEM)) == 36  # 18 raw + 18 cat
    assert len(registry.columns_in_family(MetricFamily.ENTERPRISE_LEADERSHIP_DOMAIN)) == 3
    assert len(registry.columns_in_family(MetricFamily.HIPO_COMPOSITE)) == 2
    assert len(registry.columns_in_family(MetricFamily.RATER_360)) == 40
    assert len(registry.all_outcome_columns()) == 2


def test_registry_gsa_domains_grouping(registry: FrameworkRegistry):
    domains = registry.gsa_domains()
    assert set(domains.keys()) == {str(i) for i in range(1, 9)}
    assert len(domains["1"]) == 12  # 1.1.a-d (4) + 1.2.a-h (8)
    for cols in domains.values():
        assert all(c.endswith("_skill") for c in cols)


def test_registry_rater_360_dimensions(registry: FrameworkRegistry):
    dims = registry.rater_360_dimensions()
    assert set(dims.keys()) == {str(i) for i in range(1, 9)}
    for dim, raters in dims.items():
        assert set(raters.keys()) == {"self", "manager", "report", "colleague", "other"}
        assert raters["self"] == f"360.{dim}_self"


def test_describe_for_prompt_never_invents_names(registry: FrameworkRegistry):
    described = registry.describe_for_prompt(["4_personality", "360.1_manager", "tenure_years"])
    assert "4_personality" in described
    assert "360.1_manager" in described
    assert "tenure_years" in described
    # every line must correspond to a column that actually exists
    for line in described.splitlines():
        name = line.split(" | ")[0].removeprefix("- ").strip()
        assert registry.is_real_column(name)


def test_is_real_column_rejects_invented_names(registry: FrameworkRegistry):
    assert registry.is_real_column("4_personality") is True
    assert registry.is_real_column("comp_opacity") is False
    assert registry.is_real_column("regretted_attrition") is False


# -- derived_metrics.py: real-column enforcement + real computation -----


def test_primitives_reject_invented_columns(real_df: pd.DataFrame):
    with pytest.raises(ValueError, match="non-existent column"):
        gap(real_df, "comp_opacity", "4_personality")
    with pytest.raises(ValueError, match="non-existent column"):
        ratio(real_df, "4_personality", "promo_fairness")
    with pytest.raises(ValueError, match="non-existent column"):
        composite_index(real_df, ["4_personality", "regretted_attrition"])


def test_gap_computes_real_divergence(real_df: pd.DataFrame):
    result = gap(real_df, "360.1_self", "360.1_manager")
    expected = real_df["360.1_self"] - real_df["360.1_manager"]
    pd.testing.assert_series_equal(result, expected, check_names=False)


def test_z_score_and_composite_index(real_df: pd.DataFrame):
    z = z_score(real_df, "tenure_years")
    assert abs(z.mean()) < 1e-6
    idx = composite_index(real_df, ["4_personality", "7_personality"], weights=[0.5, 0.5])
    assert len(idx) == len(real_df)


def test_banded(real_df: pd.DataFrame):
    bands = banded(real_df, "HIPO.1_bucket", [("Low", 2.5), ("Medium", 3.5), ("High", float("inf"))])
    assert set(bands.dropna().unique()) <= {"Low", "Medium", "High"}


def test_gsa_domain_rollup(real_df: pd.DataFrame, registry: FrameworkRegistry):
    domain_1_cols = registry.gsa_domains()["1"]
    rollup = gsa_domain_rollup(real_df, domain_1_cols)
    expected = real_df[domain_1_cols].mean(axis=1)
    pd.testing.assert_series_equal(rollup, expected, check_names=False)


def test_quadrant_divergence_real_360_pair(real_df: pd.DataFrame):
    result = quadrant_divergence(
        real_df, x_column="360.3_self", y_column="360.3_manager", x_threshold=3.5, y_threshold=3.5
    )
    assert result.x_column == "360.3_self"
    assert result.y_column == "360.3_manager"
    assert sum(result.quadrant_counts.values()) <= len(real_df)
    assert isinstance(result.gap_mean, float)
    assert 0.0 <= result.off_diagonal_ratio <= 1.0


def test_quadrant_divergence_rejects_invented_dimension(real_df: pd.DataFrame):
    with pytest.raises(ValueError, match="non-existent column"):
        quadrant_divergence(real_df, "actual_performance", "360.3_manager", 3.5, 3.5)
