"""The SHL Metric Framework — see docs/NEXT_VERSION_INTEGRATION_PLAN.md and
/home/aashutosh.joshi/AI-Thon/Plans/DELPHI_V2_ARCHITECTURE.md Part 4A.

The single source of truth that every insight-side agent is constrained to.
Every downstream stage (construct grounding, investigation planning,
analytics, root cause, business insight, visualization) may only reference
columns/metrics this package can prove are real — never an invented name.

Deliberately does NOT claim proprietary SHL competency labels for individual
columns (e.g. "this is Makes_Quick_Decisions") — the source data
(Book1_standardized.xlsx) uses opaque coded names (`4_personality`,
`1.1.a_skill`) with no bundled codebook mapping codes to competency names.
What IS verifiable and real, and therefore what this framework asserts,
is *structure*: assessment family, hierarchical grouping (domain/subgroup/
item), value scale, and null coverage, all computed directly from the
column name and the actual data. That is a strictly honest, weaker claim
than base-agents-strands' named-column spec, and the framework says so
rather than fabricating names to look more complete."""

from insight_pipeline.framework.derived_metrics import (
    DerivedMetric,
    DivergenceResult,
    banded,
    composite_index,
    gap,
    quadrant_divergence,
    ratio,
    z_score,
)
from insight_pipeline.framework.outcome_detection import ColumnClassification, classify_columns
from insight_pipeline.framework.registry import FrameworkRegistry
from insight_pipeline.framework.schema import MetricDefinition, MetricFamily

__all__ = [
    "MetricDefinition",
    "MetricFamily",
    "ColumnClassification",
    "classify_columns",
    "FrameworkRegistry",
    "DerivedMetric",
    "DivergenceResult",
    "composite_index",
    "gap",
    "ratio",
    "z_score",
    "banded",
    "quadrant_divergence",
]
