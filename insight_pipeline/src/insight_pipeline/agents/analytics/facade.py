"""Analytics Agent — see docs/PLATFORM_ARCHITECTURE.md §9. Dynamically
selects applicable AnalysisMethodPlugins and runs them concurrently
(mirrors hypothesis_agent's dimension-evaluator gather pattern)."""

from __future__ import annotations

import asyncio

from insight_pipeline.contracts.analytics import AnalyticsResult
from insight_pipeline.contracts.dataset import RetrievedDataset
from insight_pipeline.contracts.investigation import InvestigationPlan
from insight_pipeline.logging_setup import get_logger
from insight_pipeline.plugins.analysis_methods.base import AnalysisMethodPlugin
from insight_pipeline.plugins import PluginRegistry

logger = get_logger("agents.analytics")


class AnalyticsAgent:
    def __init__(
        self,
        method_registry: PluginRegistry[AnalysisMethodPlugin],
        max_methods: int = 6,
    ) -> None:
        self._method_registry = method_registry
        self._max_methods = max_methods

    async def run(
        self, dataset: RetrievedDataset, investigation_plan: InvestigationPlan
    ) -> AnalyticsResult:
        plugins = list(self._method_registry.all().values())
        applicability = await asyncio.gather(
            *(p.is_applicable(investigation_plan, dataset.metadata) for p in plugins)
        )
        applicable = [p for p, ok in zip(plugins, applicability) if ok][: self._max_methods]

        if not applicable:
            logger.warning("no applicable analysis methods for this investigation plan")
            return AnalyticsResult(
                investigation_plan_id=investigation_plan.id,
                dataset_id=dataset.id,
                data_quality_notes=["no analysis method was applicable to the resolved dataset"],
            )

        results = await asyncio.gather(*(p.run(dataset.handle, investigation_plan) for p in applicable))
        logger.info(
            "analytics complete",
            extra={"extra_fields": {"methods_run": [r.method for r in results]}},
        )
        return AnalyticsResult(
            investigation_plan_id=investigation_plan.id,
            dataset_id=dataset.id,
            methods_run=list(results),
            data_quality_notes=[dataset.metadata.coverage_notes] if dataset.metadata.coverage_notes else [],
        )
