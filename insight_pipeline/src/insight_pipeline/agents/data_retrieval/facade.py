"""Data Retrieval Agent — see docs/PLATFORM_ARCHITECTURE.md §8. Only job:
obtain data. No statistical reasoning happens here."""

from __future__ import annotations

from insight_pipeline.contracts.dataset import RetrievedDataset
from insight_pipeline.contracts.investigation import InvestigationPlan
from insight_pipeline.logging_setup import get_logger
from insight_pipeline.ports.dataset_retriever import DatasetRetriever

logger = get_logger("agents.data_retrieval")


class DataRetrievalAgent:
    def __init__(self, dataset_retriever: DatasetRetriever) -> None:
        self._dataset_retriever = dataset_retriever

    async def run(self, investigation_plan: InvestigationPlan) -> RetrievedDataset:
        dataset = await self._dataset_retriever.retrieve(investigation_plan)
        logger.info(
            "retrieved dataset",
            extra={
                "extra_fields": {
                    "investigation_plan_id": investigation_plan.id,
                    "row_count": dataset.handle.row_count,
                    "fields": len(dataset.metadata.fields),
                }
            },
        )
        return dataset
