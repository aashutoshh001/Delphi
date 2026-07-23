from __future__ import annotations

from insight_pipeline.contracts.analytics import AnalyticsResult
from insight_pipeline.contracts.business_insight import BusinessInsights
from insight_pipeline.contracts.visualization import VisualizationPlan, VisualizationSpec
from insight_pipeline.plugins.visualization_recommenders.base import (
    VisualizationRecommenderPlugin,
)


class RuleBasedVisualizationRecommender(VisualizationRecommenderPlugin):
    """No-LLM fallback: one chart per analysis method result that has
    exactly two variables involved (the common case for correlation/
    regression/ANOVA/chi-square), safe and minimal rather than absent."""

    strategy_name = "rule_based"

    async def recommend(
        self,
        insights: BusinessInsights,
        analytics: AnalyticsResult,
        session_id: str | None = None,
    ) -> VisualizationPlan:
        chart_type_by_method = {
            "correlation": "scatter",
            "simple_linear_regression": "scatter",
            "one_way_anova": "boxplot",
            "chi_square_independence": "bar",
            "quadrant_divergence": "quadrant_divergence",
            "rater_gap_360": "quadrant_divergence",
        }
        specs = []
        for i, result in enumerate(analytics.methods_run):
            if len(result.variables_involved) < 2:
                continue
            specs.append(
                VisualizationSpec(
                    title=f"{result.variables_involved[0]} vs {result.variables_involved[1]}",
                    business_objective="Show the relationship this analysis found.",
                    variables=result.variables_involved[:2],
                    visualization_type=chart_type_by_method.get(result.method, "bar"),
                    reason=f"Direct output of {result.method}.",
                    priority=i + 1,
                    executive_message=result.interpretation_notes,
                    expected_insight=result.interpretation_notes,
                    data_requirements=result.variables_involved[:2],
                )
            )
        return VisualizationPlan(specs=specs)
