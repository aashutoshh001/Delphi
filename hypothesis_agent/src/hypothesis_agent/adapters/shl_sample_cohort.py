"""Loads the real SHL sample assessment cohort (`Book1.xlsx`: 379 candidates
x 153 behavioral/psychometric attributes) into an `OrganizationProfile` +
`EmployeeDataLandscape` — schema-level only, per the architecture's boundary
(docs/ARCHITECTURE.md §1): the Hypothesis Agent never sees row-level employee
data, only what kinds of attributes exist and how complete each one is.

`Book1.xlsx` columns, in order:
- `Candidate_ID` (dropped — not schema info)
- 104 granular behavioral indicators, 0-5 ordinal scale (e.g. "Makes_Quick_Decisions")
- 20 aggregate competency buckets, categorical (Weakness/Sufficiency/Strength)
- 2 leadership-potential scores (Aspiration_Score_Bucket, Ability_Score_Bucket —
  named "bucket" but are numeric scores in the source file)
- 27 role/business-context fit percentiles (e.g. "Lead_Global_Cross_Cultural_Teams_pct")
"""

from __future__ import annotations

from pathlib import Path

from hypothesis_agent.contracts.organization import (
    AttributeField,
    EmployeeDataLandscape,
    OrganizationProfile,
)

ORGANIZATION_ID = "shl-sample-cohort"

_GRANULAR_COUNT = 104
_AGGREGATE_COUNT = 20
_POTENTIAL_COUNT = 2
# remainder (27 columns) are role/context fit percentiles


def _column_category(index: int) -> tuple[str, str, str]:
    """category, data_type, description for the index-th non-ID column."""
    if index < _GRANULAR_COUNT:
        return (
            "behavioural_competency",
            "ordinal",
            "Granular behavioral indicator, 0-5 scale (SHL UCF).",
        )
    index -= _GRANULAR_COUNT
    if index < _AGGREGATE_COUNT:
        return (
            "behavioural_competency",
            "categorical",
            "Aggregate competency rating bucket (Weakness/Sufficiency/Strength).",
        )
    index -= _AGGREGATE_COUNT
    if index < _POTENTIAL_COUNT:
        return (
            "psychometrics",
            "numeric",
            "Leadership potential score (aspiration/ability model).",
        )
    return (
        "organizational_fit",
        "numeric",
        "Percentile fit for a specific leadership/business context.",
    )


def load_organization_and_landscape(
    xlsx_path: Path | str = "Book1.xlsx",
) -> tuple[OrganizationProfile, EmployeeDataLandscape]:
    try:
        import openpyxl
    except ImportError as exc:
        raise ImportError(
            "load_shl_sample_cohort requires 'openpyxl': pip install openpyxl"
        ) from exc

    path = Path(xlsx_path)
    workbook = openpyxl.load_workbook(path, data_only=True, read_only=True)
    worksheet = workbook[workbook.sheetnames[0]]
    row_iter = worksheet.iter_rows(values_only=True)
    header = next(row_iter)
    data_rows = list(row_iter)
    workbook.close()

    column_names = header[1:]  # drop Candidate_ID
    non_null_counts = [0] * len(column_names)
    total = 0
    for row in data_rows:
        total += 1
        for i, value in enumerate(row[1:]):
            if value is not None and value != "":
                non_null_counts[i] += 1

    fields: list[AttributeField] = []
    for i, name in enumerate(column_names):
        category, data_type, description = _column_category(i)
        coverage = non_null_counts[i] / total if total else 0.0
        fields.append(
            AttributeField(
                name=name,
                category=category,
                data_type=data_type,
                coverage_ratio=round(coverage, 4),
                description=description,
            )
        )

    landscape = EmployeeDataLandscape(
        organization_id=ORGANIZATION_ID,
        employee_count_estimate=total,
        available_fields=fields,
        notes=(
            "Sourced from an SHL behavioral competency + leadership potential "
            "assessment export (Universal Competency Framework style), plus "
            "role/business-context fit percentiles against ~27 contexts."
        ),
    )
    profile = OrganizationProfile(
        organization_id=ORGANIZATION_ID,
        name="SHL Sample Assessment Cohort",
        core_attributes={
            "industry": "talent assessment / people analytics (sample candidate cohort)",
            "data_source": "SHL behavioral competency + leadership potential assessment export",
            "competency_framework": "SHL Universal Competency Framework (UCF)",
            "structure": f"{total} assessed candidates; no formal org hierarchy in this sample",
            "business_goals": [
                "identify high-potential talent for leadership pipelines",
                "understand which competencies predict fit for specific business contexts",
            ],
        },
    )
    return profile, landscape


if __name__ == "__main__":
    profile, landscape = load_organization_and_landscape()
    print(f"organization_id={profile.organization_id!r} name={profile.name!r}")
    print(f"employee_count_estimate={landscape.employee_count_estimate}")
    print(f"available_fields={len(landscape.available_fields)}")
    for category in sorted(landscape.categories()):
        count = sum(1 for f in landscape.available_fields if f.category == category)
        print(f"  {category}: {count} fields")
