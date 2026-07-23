from insight_pipeline.adapters.employee_data.handle_cache import InMemoryDatasetHandleCache
from insight_pipeline.plugins.analysis_methods.anova import ANOVAPlugin
from insight_pipeline.plugins.analysis_methods.base import AnalysisMethodPlugin
from insight_pipeline.plugins.analysis_methods.chi_square import ChiSquarePlugin
from insight_pipeline.plugins.analysis_methods.correlation import CorrelationPlugin
from insight_pipeline.plugins.analysis_methods.descriptive_stats import DescriptiveStatsPlugin
from insight_pipeline.plugins.analysis_methods.quadrant_divergence import QuadrantDivergencePlugin
from insight_pipeline.plugins.analysis_methods.rater_gap import RaterGapPlugin
from insight_pipeline.plugins.analysis_methods.regression import RegressionPlugin
from insight_pipeline.plugins import PluginRegistry


def default_analysis_method_registry(
    handle_cache: InMemoryDatasetHandleCache,
) -> PluginRegistry[AnalysisMethodPlugin]:
    """The multi-angle library (V2 architecture plan Part 4D): the original
    four hypothesis-testing methods (correlation, regression, ANOVA,
    chi-square) plus three SHL-grounded breadth methods (descriptive_stats,
    quadrant_divergence, rater_gap_360). AnalyticsAgent already runs every
    *applicable* registered method concurrently and caps the total via
    `max_methods` — that existing concurrent-execution + applicability-
    filtering behavior IS the "multi-angle fan-out with an entropy/diversity
    cap" the architecture plan describes, achieved via registry growth
    rather than a separate LangGraph Send() fan-out. New angles (clustering,
    survival analysis, feature importance, ...) are future plugins, added
    with zero change to the Analytics Agent itself."""
    registry: PluginRegistry[AnalysisMethodPlugin] = PluginRegistry(kind="analysis_method")
    registry.register("correlation", CorrelationPlugin(handle_cache))
    registry.register("simple_linear_regression", RegressionPlugin(handle_cache))
    registry.register("one_way_anova", ANOVAPlugin(handle_cache))
    registry.register("chi_square_independence", ChiSquarePlugin(handle_cache))
    registry.register("descriptive_stats", DescriptiveStatsPlugin(handle_cache))
    registry.register("quadrant_divergence", QuadrantDivergencePlugin(handle_cache))
    registry.register("rater_gap_360", RaterGapPlugin(handle_cache))
    return registry


__all__ = [
    "ANOVAPlugin",
    "AnalysisMethodPlugin",
    "ChiSquarePlugin",
    "CorrelationPlugin",
    "DescriptiveStatsPlugin",
    "QuadrantDivergencePlugin",
    "RaterGapPlugin",
    "RegressionPlugin",
    "default_analysis_method_registry",
]
