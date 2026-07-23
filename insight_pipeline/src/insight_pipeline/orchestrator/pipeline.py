"""InvestigationPipeline — the platform's public interface, the downstream
analog of hypothesis_agent.agent.HypothesisAgent. `run()` takes a
HypothesisPackage and returns exactly one InsightPackage, persisting it."""

from __future__ import annotations

from hypothesis_agent.contracts.hypothesis import HypothesisPackage
from insight_pipeline.contracts.insight_package import InsightPackage
from insight_pipeline.di.container import PipelineDependencies
from insight_pipeline.logging_setup import configure_logging, get_logger
from insight_pipeline.orchestrator.graph import build_pipeline_graph
from insight_pipeline.orchestrator.state import PipelineState

logger = get_logger("orchestrator.pipeline")


class InvestigationPipeline:
    def __init__(self, dependencies: PipelineDependencies) -> None:
        self._deps = dependencies
        configure_logging(dependencies.config.logging.level, dependencies.config.logging.structured)

    @property
    def dependencies(self) -> PipelineDependencies:
        return self._deps

    async def run(self, hypothesis_package: HypothesisPackage) -> InsightPackage:
        graph = build_pipeline_graph(self._deps)
        initial_state: PipelineState = {"hypothesis_package": hypothesis_package, "trace": []}
        logger.info(
            "starting investigation",
            extra={"extra_fields": {"hypothesis_package_id": hypothesis_package.package_id}},
        )

        final_state = await graph.ainvoke(initial_state, config={"recursion_limit": 50})

        package = InsightPackage(
            hypothesis_package=hypothesis_package,
            investigation_plan=final_state["investigation_plan"],
            analytics_results=final_state["analytics_result"],
            root_cause_graph=final_state["root_cause_graph"],
            business_insights=final_state["business_insights"],
            narrative=final_state["narrative"],
            visualization_plan=final_state["visualization_plan"],
            generated_figures=final_state.get("generated_figures", []),
            trace=final_state.get("trace", []),
            metadata={"config_snapshot": self._deps.config.model_dump()},
        )
        await self._deps.insight_package_repository.save(package)

        logger.info(
            "investigation complete",
            extra={
                "extra_fields": {
                    "insight_package_id": package.id,
                    "figures": len(package.generated_figures),
                }
            },
        )
        return package
