from abc import ABC, abstractmethod

from insight_pipeline.contracts.dataset import DatasetHandle
from insight_pipeline.contracts.visualization import ResolvedChartData, VisualizationSpec


class ChartDataResolver(ABC):
    """The one place per figure that touches the raw dataset — aggregates a
    DatasetHandle down into small, chart-ready, framework-agnostic data.
    Adapter-internal pandas/numpy use is fine here; the return type is not."""

    @abstractmethod
    async def resolve(
        self, spec: VisualizationSpec, handle: DatasetHandle
    ) -> ResolvedChartData: ...
