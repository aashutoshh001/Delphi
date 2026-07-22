from hypothesis_agent.contracts.hypothesis import (
    CritiqueResult,
    EvaluationScorecard,
    HypothesisCandidate,
    HypothesisPackage,
    SearchStatistics,
)
from hypothesis_agent.contracts.memory import HistoricalHypothesisRecord
from hypothesis_agent.contracts.organization import EmployeeDataLandscape, OrganizationProfile


def test_organization_profile_accepts_arbitrary_attributes():
    profile = OrganizationProfile(
        organization_id="org-1",
        core_attributes={"industry": "fintech", "future_field_nobody_predicted": {"nested": True}},
    )
    assert profile.core_attributes["future_field_nobody_predicted"] == {"nested": True}


def test_employee_data_landscape_never_carries_row_level_data():
    landscape = EmployeeDataLandscape(organization_id="org-1")
    assert landscape.available_fields == []
    assert landscape.categories() == set()


def test_hypothesis_candidate_composite_score_defaults_to_zero_without_scorecard():
    candidate = HypothesisCandidate(lens="burnout_resilience", statement="x")
    assert candidate.composite_score() == 0.0


def test_hypothesis_package_round_trips_through_json():
    scorecard = EvaluationScorecard(business_value=0.8, composite=0.5)
    package = HypothesisPackage(
        organization_id="org-1",
        hypothesis_statement="stmt",
        mechanism_explanation="mech",
        business_lens="burnout_resilience",
        scorecard=scorecard,
        critique=CritiqueResult(),
        search_stats=SearchStatistics(),
    )
    restored = HypothesisPackage.model_validate_json(package.model_dump_json())
    assert restored.hypothesis_statement == "stmt"
    assert restored.scorecard.business_value == 0.8


def test_historical_hypothesis_record_optional_scorecard_forward_ref_resolves():
    record = HistoricalHypothesisRecord(statement="s", lens="burnout_resilience")
    assert record.scorecard is None
