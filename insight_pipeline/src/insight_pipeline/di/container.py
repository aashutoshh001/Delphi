"""The only module allowed to import every adapter — turns an already-built
hypothesis_agent AgentDependencies (LLM/embedding config lives there, shared
by the whole platform, not reconfigured twice) + a PipelineConfig into a
fully wired PipelineDependencies."""

from __future__ import annotations

from dataclasses import dataclass

from hypothesis_agent.ports.embedding_service import EmbeddingService
from hypothesis_agent.ports.employee_repository import EmployeeRepository
from hypothesis_agent.ports.llm_service import LLMService
from hypothesis_agent.reasoning.dependencies import AgentDependencies
from insight_pipeline.adapters.dataset_retrieval.default_retriever import DefaultDatasetRetriever
from insight_pipeline.adapters.employee_data.excel_repository import ExcelEmployeeDataRepository
from insight_pipeline.adapters.employee_data.handle_cache import InMemoryDatasetHandleCache
from insight_pipeline.adapters.investigation_planner.direct_llm_engine import (
    DirectLLMInvestigationPlanner,
)
from insight_pipeline.adapters.organization_knowledge.embedding_retriever import (
    EmbeddingOrganizationKnowledgeRetriever,
)
from insight_pipeline.adapters.organization_knowledge.in_memory_repository import (
    InMemoryOrganizationKnowledgeRepository,
)
from insight_pipeline.adapters.plotting.matplotlib_engine import MatplotlibPlottingEngine
from insight_pipeline.adapters.query_planning.direct_llm_planner import DirectLLMQueryPlanner
from insight_pipeline.config.settings import PipelineConfig
from insight_pipeline.plugins.analysis_methods import default_analysis_method_registry
from insight_pipeline.plugins.analysis_methods.base import AnalysisMethodPlugin
from insight_pipeline.plugins.business_evaluators.llm_synthesis import LLMBusinessSynthesisEvaluator
from insight_pipeline.plugins.narrative_strategies.balanced import BalancedNarrativeStrategy
from insight_pipeline.plugins import PluginRegistry
from insight_pipeline.plugins.root_cause_strategies.llm_mechanism_brainstorm import (
    LLMMechanismBrainstormPlugin,
)
from insight_pipeline.plugins.visualization_recommenders.llm_recommender import (
    LLMVisualizationRecommender,
)
from insight_pipeline.ports.dataset_retriever import DatasetRetriever
from insight_pipeline.ports.insight_package_repository import InsightPackageRepository
from insight_pipeline.ports.investigation_planner_engine import InvestigationPlannerEngine
from insight_pipeline.ports.organization_knowledge_repository import (
    OrganizationKnowledgeRepository,
)
from insight_pipeline.ports.organization_knowledge_retriever import (
    OrganizationKnowledgeRetriever,
)
from insight_pipeline.ports.plotting_engine import PlottingEngine
from insight_pipeline.prompts.registry import PromptRegistry, default_prompt_registry


@dataclass
class PipelineDependencies:
    llm_service: LLMService
    embedding_service: EmbeddingService
    employee_repository: EmployeeRepository
    knowledge_repository: OrganizationKnowledgeRepository
    knowledge_retriever: OrganizationKnowledgeRetriever
    dataset_retriever: DatasetRetriever
    handle_cache: InMemoryDatasetHandleCache
    analysis_method_registry: PluginRegistry[AnalysisMethodPlugin]
    investigation_planner_engine: InvestigationPlannerEngine
    root_cause_strategy: LLMMechanismBrainstormPlugin
    business_evaluators: list[LLMBusinessSynthesisEvaluator]
    narrative_strategy: BalancedNarrativeStrategy
    visualization_recommender: LLMVisualizationRecommender
    plotting_engine: PlottingEngine
    insight_package_repository: InsightPackageRepository
    prompts: PromptRegistry
    config: PipelineConfig


def build_pipeline_dependencies(
    hypothesis_deps: AgentDependencies, config: PipelineConfig | None = None
) -> PipelineDependencies:
    cfg = config or PipelineConfig.load()
    prompts = default_prompt_registry()
    llm_service = hypothesis_deps.llm_service
    embedding_service = hypothesis_deps.embedding_service

    knowledge_repository = InMemoryOrganizationKnowledgeRepository()
    knowledge_retriever = EmbeddingOrganizationKnowledgeRetriever(knowledge_repository, embedding_service)

    handle_cache = InMemoryDatasetHandleCache()
    employee_data_repository = ExcelEmployeeDataRepository(cfg.backends.excel_path, handle_cache)
    query_planner = DirectLLMQueryPlanner(llm_service, prompts)
    dataset_retriever = DefaultDatasetRetriever(
        hypothesis_deps.employee_repository, query_planner, employee_data_repository
    )

    from insight_pipeline.adapters.insight_store.json_insight_store import JsonInsightStore

    return PipelineDependencies(
        llm_service=llm_service,
        embedding_service=embedding_service,
        employee_repository=hypothesis_deps.employee_repository,
        knowledge_repository=knowledge_repository,
        knowledge_retriever=knowledge_retriever,
        dataset_retriever=dataset_retriever,
        handle_cache=handle_cache,
        analysis_method_registry=default_analysis_method_registry(handle_cache),
        investigation_planner_engine=DirectLLMInvestigationPlanner(llm_service, prompts),
        root_cause_strategy=LLMMechanismBrainstormPlugin(llm_service, prompts),
        business_evaluators=[LLMBusinessSynthesisEvaluator(llm_service, prompts)],
        narrative_strategy=BalancedNarrativeStrategy(llm_service, prompts),
        visualization_recommender=LLMVisualizationRecommender(llm_service, prompts),
        plotting_engine=MatplotlibPlottingEngine(cfg.visualization.figure_output_dir),
        insight_package_repository=JsonInsightStore(cfg.backends.insight_store_path),
        prompts=prompts,
        config=cfg,
    )
