from abc import ABC, abstractmethod

from insight_pipeline.contracts.visualization import (
    ChartTheme,
    GeneratedFigure,
    ResolvedChartData,
    VisualizationSpec,
)


class PlottingEngine(ABC):
    """Deterministic rendering only — no reasoning. The agent decides WHAT
    (VisualizationSpec); this port decides nothing, it just draws."""

    @abstractmethod
    async def render(
        self, spec: VisualizationSpec, data: ResolvedChartData, theme: ChartTheme
    ) -> GeneratedFigure: ...

    @abstractmethod
    def supports(self, visualization_type: str) -> bool: ...
