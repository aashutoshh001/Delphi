from insight_pipeline.adapters.employee_data.handle_cache import InMemoryDatasetHandleCache
from insight_pipeline.plugins.analysis_methods.anova import ANOVAPlugin
from insight_pipeline.plugins.analysis_methods.base import AnalysisMethodPlugin
from insight_pipeline.plugins.analysis_methods.chi_square import ChiSquarePlugin
from insight_pipeline.plugins.analysis_methods.correlation import CorrelationPlugin
from insight_pipeline.plugins.analysis_methods.regression import RegressionPlugin
from insight_pipeline.plugins import PluginRegistry


def default_analysis_method_registry(
    handle_cache: InMemoryDatasetHandleCache,
) -> PluginRegistry[AnalysisMethodPlugin]:
    """First four methods (correlation, regression, ANOVA, chi-square) per
    docs/PLATFORM_ARCHITECTURE.md §23 phase 5 — clustering, survival
    analysis, feature importance, time series, mixed effects,
    dimensionality reduction, and decision trees are future plugins, added
    with zero change to the Analytics Agent itself."""
    registry: PluginRegistry[AnalysisMethodPlugin] = PluginRegistry(kind="analysis_method")
    registry.register("correlation", CorrelationPlugin(handle_cache))
    registry.register("simple_linear_regression", RegressionPlugin(handle_cache))
    registry.register("one_way_anova", ANOVAPlugin(handle_cache))
    registry.register("chi_square_independence", ChiSquarePlugin(handle_cache))
    return registry


__all__ = [
    "ANOVAPlugin",
    "AnalysisMethodPlugin",
    "ChiSquarePlugin",
    "CorrelationPlugin",
    "RegressionPlugin",
    "default_analysis_method_registry",
]
