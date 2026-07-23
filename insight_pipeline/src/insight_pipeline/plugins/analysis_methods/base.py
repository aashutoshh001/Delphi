from abc import ABC, abstractmethod

from insight_pipeline.contracts.analytics import AnalysisMethodResult
from insight_pipeline.contracts.dataset import DatasetHandle, DatasetMetadata
from insight_pipeline.contracts.investigation import InvestigationPlan


class AnalysisMethodPlugin(ABC):
    """One statistical method. Uniform interface, mirrors the Hypothesis
    Agent's Evaluator plugins exactly: `is_applicable` decides whether this
    method makes sense for this plan/dataset shape, `run` executes it.
    Adapter-internal code may use numpy/scipy/pandas freely — only the
    return type is constrained."""

    method_name: str

    @abstractmethod
    async def is_applicable(
        self, plan: InvestigationPlan, metadata: DatasetMetadata
    ) -> bool: ...

    @abstractmethod
    async def run(
        self, handle: DatasetHandle, plan: InvestigationPlan
    ) -> AnalysisMethodResult: ...
