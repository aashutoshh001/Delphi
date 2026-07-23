"""The Plot Generation Tool itself — deterministic execution only, no
reasoning (docs/PLATFORM_ARCHITECTURE.md §14). Ties ChartDataResolver +
PlottingEngine together: the agent decided WHAT (VisualizationSpec); this
resolves the data and draws it, nothing more."""

from __future__ import annotations

from insight_pipeline.contracts.dataset import DatasetHandle
from insight_pipeline.contracts.visualization import ChartTheme, GeneratedFigure, VisualizationSpec
from insight_pipeline.logging_setup import get_logger
from insight_pipeline.ports.chart_data_resolver import ChartDataResolver
from insight_pipeline.ports.plotting_engine import PlottingEngine

logger = get_logger("tools.plot_generation")


class PlotGenerationTool:
    def __init__(
        self,
        resolver: ChartDataResolver,
        engine: PlottingEngine,
        theme: ChartTheme | None = None,
    ) -> None:
        self._resolver = resolver
        self._engine = engine
        self._theme = theme or ChartTheme()

    async def render(self, spec: VisualizationSpec, handle: DatasetHandle) -> GeneratedFigure | None:
        if not self._engine.supports(spec.visualization_type):
            logger.warning(
                "no renderer for visualization type — skipping",
                extra={"extra_fields": {"visualization_type": spec.visualization_type, "spec_id": spec.id}},
            )
            return None
        data = await self._resolver.resolve(spec, handle)
        figure = await self._engine.render(spec, data, self._theme)
        logger.info("figure rendered", extra={"extra_fields": {"spec_id": spec.id, "file_ref": figure.file_ref}})
        return figure
