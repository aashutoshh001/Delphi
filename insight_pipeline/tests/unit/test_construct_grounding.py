from pathlib import Path

import pandas as pd
import pytest

from hypothesis_agent.adapters.llm.mock_llm_service import MockLLMService
from hypothesis_agent.contracts.hypothesis import (
    CritiqueResult,
    EvaluationScorecard,
    HypothesisPackage,
    SearchStatistics,
)

from insight_pipeline.adapters.construct_grounding.direct_llm_engine import (
    DirectLLMConstructGroundingEngine,
)
from insight_pipeline.agents.construct_grounding.facade import ConstructGroundingAgent
from insight_pipeline.framework.registry import FrameworkRegistry
from insight_pipeline.prompts.registry import default_prompt_registry

_XLSX_PATH = Path(__file__).parents[3] / "Book1_standardized.xlsx"
pytestmark = pytest.mark.skipif(not _XLSX_PATH.exists(), reason="Book1_standardized.xlsx not present")


def _hypothesis_package() -> HypothesisPackage:
    return HypothesisPackage(
        organization_id="org-1",
        hypothesis_statement="Employees with a large gap between self-rated and manager-rated performance show higher regretted attrition.",
        mechanism_explanation="Perception mismatch drives disengagement.",
        business_lens="compensation_fairness",
        target_constructs=["compensation opacity", "regretted attrition", "self-manager rating gap"],
        scorecard=EvaluationScorecard(composite=0.7),
        critique=CritiqueResult(),
        search_stats=SearchStatistics(),
    )


@pytest.fixture(scope="module")
def registry() -> FrameworkRegistry:
    return FrameworkRegistry.from_dataframe(pd.read_excel(_XLSX_PATH))


async def test_grounding_map_never_contains_invented_columns(registry: FrameworkRegistry):
    llm = MockLLMService()
    engine = DirectLLMConstructGroundingEngine(llm, default_prompt_registry())
    agent = ConstructGroundingAgent(engine)

    grounding_map = await agent.run(_hypothesis_package(), registry)

    for construct in grounding_map.grounded:
        for column in construct.columns:
            assert registry.is_real_column(column), f"invented column leaked through: {column}"
    # every grounded/ungrounded construct traces back to the hypothesis
    all_constructs = {c.construct_name for c in grounding_map.grounded} | {
        c.construct_name for c in grounding_map.ungrounded
    }
    assert all_constructs  # non-empty: mock LLM fabricates something for every field


async def test_grounding_map_filters_llm_invented_names_directly():
    """Bypasses the LLM to test the filtering logic in isolation: feed a
    response with a mix of real and invented column names, confirm only
    real ones survive and the invented ones land in rejected_column_names."""
    import pandas as pd

    from insight_pipeline.adapters.construct_grounding.direct_llm_engine import (
        _GroundedConstructResponse,
        _GroundingResponse,
        _UngroundedConstructResponse,
    )

    class _StubLLM:
        async def complete_structured(self, request, schema):
            return _GroundingResponse(
                grounded=[
                    _GroundedConstructResponse(
                        construct_name="leadership readiness",
                        columns=["4_personality", "comp_opacity", "HIPO.1_bucket"],
                        role="independent",
                        rationale="test",
                    ),
                    _GroundedConstructResponse(
                        construct_name="totally fake construct",
                        columns=["regretted_attrition", "promo_fairness"],
                        role="dependent",
                        rationale="test",
                    ),
                ],
                ungrounded=[_UngroundedConstructResponse(construct_name="ambiguity tolerance", reason="no proxy")],
            )

    df = pd.DataFrame({"4_personality": [1, 2], "HIPO.1_bucket": [3.0, 4.0], "candidate_id": ["a", "b"]})
    registry = FrameworkRegistry.from_dataframe(df)
    engine = DirectLLMConstructGroundingEngine(_StubLLM(), default_prompt_registry())
    agent = ConstructGroundingAgent(engine)

    grounding_map = await agent.run(_hypothesis_package(), registry)

    grounded_names = {g.construct_name for g in grounding_map.grounded}
    assert grounded_names == {"leadership readiness"}
    leadership = next(g for g in grounding_map.grounded if g.construct_name == "leadership readiness")
    assert set(leadership.columns) == {"4_personality", "HIPO.1_bucket"}
    assert "comp_opacity" not in leadership.columns
    assert "comp_opacity" in grounding_map.rejected_column_names

    ungrounded_names = {u.construct_name for u in grounding_map.ungrounded}
    assert "totally fake construct" in ungrounded_names  # zero valid columns -> demoted to ungrounded
    assert "ambiguity tolerance" in ungrounded_names
    assert "regretted_attrition" in grounding_map.rejected_column_names
    assert "promo_fairness" in grounding_map.rejected_column_names
