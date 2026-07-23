"""Column-name parsing for the standardized SHL cohort export
(Book1_standardized.xlsx). One regex per assessment family, matched against
the *real* column names actually present in the sheet — a column that
doesn't match any pattern is `MetricFamily.UNKNOWN`, never silently dropped
or silently guessed at (see outcome_detection.py for how UNKNOWN columns are
surfaced instead of analyzed).

Confirmed structure (docs/NEXT_VERSION_INTEGRATION_PLAN.md, Part 5 of the
architecture plan), from direct inspection of the file:

- `{1-8}_personality`            8   OPQ Great-8 domain scores (already-aggregated)
- `{domain}.{sub}_personality`   28  OPQ facet scores feeding the domains above
- `{domain}.{group}.{item}_skill` 96 GSA self-report skill items, grouped under
                                      8 domains (same 1-8 numbering as OPQ)
- `LC.{category}.{item}_pct`     27  Leader-Challenge percentile fit, grouped
                                      under 4 challenge categories
- `MQ.{facet}.{n}_raw`/`_cat`    18+18 Motivation Questionnaire items, grouped
                                      under 4 lettered facets (E/I/S/X)
- `EL.{1-3}_sten`                3   Enterprise-Leadership domain composites
- `HIPO.{1-2}_bucket`            2   High-Potential composite scores
- `360.{1-8}_{rater}`            40  8 dimensions x 5 rater perspectives
                                      (self/manager/report/colleague/other)
- `candidate_id`                 1   identity
- `tenure_years`, `compensation_annual_usd`  HR outcomes (see outcome_detection.py)
"""

from __future__ import annotations

import re
from enum import Enum

from pydantic import BaseModel, Field


class MetricFamily(str, Enum):
    OPQ_DOMAIN = "opq_domain"  # {1-8}_personality — Great-8, already aggregated
    OPQ_FACET = "opq_facet"  # {d.s}_personality — sub-scale feeding a domain
    GSA_SKILL_ITEM = "gsa_skill_item"  # {d.g.i}_skill — granular self-report item
    LEADER_CHALLENGE_FIT = "leader_challenge_fit"  # LC.{c.i}_pct
    MOTIVATION_ITEM = "motivation_item"  # MQ.{facet.n}_raw / _cat
    ENTERPRISE_LEADERSHIP_DOMAIN = "enterprise_leadership_domain"  # EL.{1-3}_sten
    HIPO_COMPOSITE = "hipo_composite"  # HIPO.{1-2}_bucket
    RATER_360 = "rater_360"  # 360.{1-8}_{rater}
    IDENTITY = "identity"
    OUTCOME = "outcome"
    UNKNOWN = "unknown"


_RATER_TYPES = ("self", "manager", "report", "colleague", "other")

_PATTERNS: list[tuple[MetricFamily, re.Pattern]] = [
    (MetricFamily.OPQ_DOMAIN, re.compile(r"^(?P<domain>\d+)_personality$")),
    (MetricFamily.OPQ_FACET, re.compile(r"^(?P<domain>\d+)\.(?P<sub>\d+)_personality$")),
    (MetricFamily.GSA_SKILL_ITEM, re.compile(r"^(?P<domain>\d+)\.(?P<group>\d+)\.(?P<item>[a-z])_skill$")),
    (MetricFamily.LEADER_CHALLENGE_FIT, re.compile(r"^LC\.(?P<category>\d+)\.(?P<item>[a-z])_pct$")),
    (
        MetricFamily.MOTIVATION_ITEM,
        re.compile(r"^MQ\.(?P<facet>[A-Z])\.(?P<n>\d+)_(?P<variant>raw|cat)$"),
    ),
    (MetricFamily.ENTERPRISE_LEADERSHIP_DOMAIN, re.compile(r"^EL\.(?P<index>\d+)_sten$")),
    (MetricFamily.HIPO_COMPOSITE, re.compile(r"^HIPO\.(?P<index>\d+)_bucket$")),
    (
        MetricFamily.RATER_360,
        re.compile(r"^360\.(?P<dimension>\d+)_(?P<rater>self|manager|report|colleague|other)$"),
    ),
]

_IDENTITY_NAMES = {"candidate_id"}
# Outcome names are also handled by outcome_detection.py's broader pattern list;
# this is just the confirmed set present in Book1_standardized.xlsx today.
_KNOWN_OUTCOME_NAMES = {"tenure_years", "compensation_annual_usd"}


class MetricDefinition(BaseModel):
    """What is verifiably true about one real column — never a fabricated
    competency label. `semantic_description` is generated from structure
    only (family + hierarchy position), not from an assumed SHL codebook."""

    name: str
    family: MetricFamily
    hierarchy: dict[str, str] = Field(default_factory=dict)
    scale_min: float | None = None
    scale_max: float | None = None
    coverage_ratio: float = 1.0
    semantic_description: str = ""
    stability_note: str = ""


_STABILITY_NOTES = {
    MetricFamily.OPQ_DOMAIN: "OPQ-derived personality potential — stable 3-5 years.",
    MetricFamily.OPQ_FACET: "OPQ-derived personality facet — stable 3-5 years.",
    MetricFamily.GSA_SKILL_ITEM: "GSA self-reported current behaviour — stable 12-18 months.",
    MetricFamily.LEADER_CHALLENGE_FIT: "OPQ-derived contextual fit for one of SHL's Leader Challenges.",
    MetricFamily.MOTIVATION_ITEM: "Motivation Questionnaire item — motivational driver, not a skill.",
    MetricFamily.ENTERPRISE_LEADERSHIP_DOMAIN: "OPQ-derived leadership-domain composite.",
    MetricFamily.HIPO_COMPOSITE: "Composite High-Potential score, computed upstream from OPQ+MQ inputs.",
    MetricFamily.RATER_360: "Self-rated or observer-rated (manager/report/colleague/other) — a perception, not a test score.",
}


def _semantic_description(family: MetricFamily, hierarchy: dict[str, str]) -> str:
    if family is MetricFamily.OPQ_DOMAIN:
        return f"OPQ Great-8 domain {hierarchy['domain']} of 8 (personality-derived potential, already aggregated)."
    if family is MetricFamily.OPQ_FACET:
        return f"OPQ facet {hierarchy['sub']} under Great-8 domain {hierarchy['domain']} of 8."
    if family is MetricFamily.GSA_SKILL_ITEM:
        return (
            f"GSA self-report skill item {hierarchy['item']} in sub-group {hierarchy['group']} "
            f"under Great-8 domain {hierarchy['domain']} of 8 (current-behaviour self-report)."
        )
    if family is MetricFamily.LEADER_CHALLENGE_FIT:
        return f"Leader-Challenge percentile fit, item {hierarchy['item']} in challenge category {hierarchy['category']} of 4."
    if family is MetricFamily.MOTIVATION_ITEM:
        return f"Motivation Questionnaire item {hierarchy['n']} in facet group '{hierarchy['facet']}'."
    if family is MetricFamily.ENTERPRISE_LEADERSHIP_DOMAIN:
        return f"Enterprise Leadership domain composite {hierarchy['index']} of 3 (sten score)."
    if family is MetricFamily.HIPO_COMPOSITE:
        return f"High-Potential composite score {hierarchy['index']} of 2 (Aspiration/Ability model)."
    if family is MetricFamily.RATER_360:
        return f"360-degree rating, dimension {hierarchy['dimension']} of 8, rater perspective: {hierarchy['rater']}."
    if family is MetricFamily.IDENTITY:
        return "Candidate identity key."
    if family is MetricFamily.OUTCOME:
        return "HR outcome column."
    return "Column present in the data but not matched to a known SHL assessment family."


def classify_column_name(name: str) -> tuple[MetricFamily, dict[str, str]]:
    """Pure name-based classification — no DataFrame access. Returns
    (family, hierarchy) where hierarchy is empty for identity/outcome/unknown."""
    if name in _IDENTITY_NAMES:
        return MetricFamily.IDENTITY, {}
    if name in _KNOWN_OUTCOME_NAMES:
        return MetricFamily.OUTCOME, {}
    for family, pattern in _PATTERNS:
        match = pattern.match(name)
        if match:
            return family, match.groupdict()
    return MetricFamily.UNKNOWN, {}


def build_metric_definition(
    name: str,
    scale_min: float | None = None,
    scale_max: float | None = None,
    coverage_ratio: float = 1.0,
) -> MetricDefinition:
    family, hierarchy = classify_column_name(name)
    return MetricDefinition(
        name=name,
        family=family,
        hierarchy=hierarchy,
        scale_min=scale_min,
        scale_max=scale_max,
        coverage_ratio=coverage_ratio,
        semantic_description=_semantic_description(family, hierarchy),
        stability_note=_STABILITY_NOTES.get(family, ""),
    )
