"""The only module allowed to import both `adapters/` and `reasoning/`. Turns
an `AgentConfig` into a fully wired `AgentDependencies`. Adding a new backend
for any port is a one-line addition to the relevant factory map below —
never a change to `reasoning/`."""

from __future__ import annotations

import os
import random
from pathlib import Path
from typing import Callable

from dotenv import load_dotenv

from hypothesis_agent.adapters.analysis_agent_gateway import NoOpAnalysisAgentGateway
from hypothesis_agent.adapters.embeddings.hash_embedding_service import HashEmbeddingService
from hypothesis_agent.adapters.embeddings.openai_embedding_service import (
    OpenAIEmbeddingService,
)
from hypothesis_agent.adapters.llm.litellm_llm_service import LiteLLMService
from hypothesis_agent.adapters.llm.mock_llm_service import MockLLMService
from hypothesis_agent.adapters.llm.openai_llm_service import OpenAILLMService
from hypothesis_agent.adapters.repositories.in_memory_employee_repository import (
    InMemoryEmployeeRepository,
)
from hypothesis_agent.adapters.repositories.in_memory_feedback_repository import (
    InMemoryFeedbackRepository,
)
from hypothesis_agent.adapters.repositories.in_memory_historical_memory_repository import (
    InMemoryHistoricalMemoryRepository,
)
from hypothesis_agent.adapters.repositories.in_memory_organization_repository import (
    InMemoryOrganizationRepository,
)
from hypothesis_agent.adapters.repositories.json_hypothesis_store import (
    JsonHypothesisStore,
)
from hypothesis_agent.adapters.understanding.deep_agent_understanding_engine import (
    DeepAgentUnderstandingEngine,
)
from hypothesis_agent.adapters.understanding.direct_llm_understanding_engine import (
    DirectLLMUnderstandingEngine,
)
from hypothesis_agent.config.settings import AgentConfig
from hypothesis_agent.plugins import ReasoningPlugins
from hypothesis_agent.plugins.business_lens import default_lens_registry
from hypothesis_agent.plugins.critics.base import Critic
from hypothesis_agent.plugins.critics.checklist_critic import ChecklistCritic
from hypothesis_agent.plugins.evaluators import default_evaluator_registry
from hypothesis_agent.plugins.memory_policies.soft_prior_policy import SoftPriorPolicy
from hypothesis_agent.plugins.search_heuristics.entropy_heuristic import (
    EntropyMaximizingHeuristic,
)
from hypothesis_agent.ports.analysis_agent_gateway import AnalysisAgentGateway
from hypothesis_agent.ports.embedding_service import EmbeddingService
from hypothesis_agent.ports.employee_repository import EmployeeRepository
from hypothesis_agent.ports.feedback_repository import FeedbackRepository
from hypothesis_agent.ports.historical_memory_repository import (
    HistoricalMemoryRepository,
)
from hypothesis_agent.ports.llm_service import LLMService
from hypothesis_agent.ports.organization_repository import OrganizationRepository
from hypothesis_agent.ports.understanding_engine import UnderstandingEngine
from hypothesis_agent.prompts.registry import default_prompt_registry
from hypothesis_agent.reasoning.dependencies import AgentDependencies

# hypothesis_agent/.env, regardless of the caller's cwd — explicit path so a
# server started from the Delphi/ repo root (its documented run location)
# still picks up keys stored in hypothesis_agent/.env. Never overrides
# already-exported env vars.
load_dotenv(Path(__file__).resolve().parents[3] / ".env", override=False)

_LLM_BACKENDS: dict[str, Callable[[AgentConfig], LLMService]] = {
    "mock": lambda cfg: MockLLMService(),
    "openai": lambda cfg: OpenAILLMService(model=cfg.llm.model),
    # Reads LITELLM_API_KEY / LITELLM_API_BASE so the same adapter works
    # whether that key is for a self-hosted LiteLLM proxy (set LITELLM_API_BASE)
    # or a direct provider litellm routes to by model name (leave it unset).
    "litellm": lambda cfg: LiteLLMService(
        model=cfg.llm.model,
        api_key=os.environ.get("LITELLM_API_KEY"),
        api_base=os.environ.get("LITELLM_API_BASE"),
    ),
}

_EMBEDDING_BACKENDS: dict[str, Callable[[AgentConfig], EmbeddingService]] = {
    "hash": lambda cfg: HashEmbeddingService(dimensions=cfg.embedding.dimensions),
    "openai": lambda cfg: OpenAIEmbeddingService(model=cfg.embedding.model),
}

_ORGANIZATION_REPOSITORY_BACKENDS: dict[str, Callable[[AgentConfig], OrganizationRepository]] = {
    "in_memory": lambda cfg: InMemoryOrganizationRepository(),
}

_EMPLOYEE_REPOSITORY_BACKENDS: dict[str, Callable[[AgentConfig], EmployeeRepository]] = {
    "in_memory": lambda cfg: InMemoryEmployeeRepository(),
}

_ANALYSIS_GATEWAY_BACKENDS: dict[str, Callable[[AgentConfig], AnalysisAgentGateway]] = {
    "noop": lambda cfg: NoOpAnalysisAgentGateway(),
}


def _build_historical_memory_repository(
    key: str, cfg: AgentConfig, embedding_service: EmbeddingService
) -> HistoricalMemoryRepository:
    if key == "in_memory":
        return InMemoryHistoricalMemoryRepository()
    if key == "json_file":
        return JsonHypothesisStore(cfg.backends.json_store_path, embedding_service)
    raise KeyError(f"unknown historical_memory_repository backend '{key}'")


def _build_feedback_repository(
    key: str, cfg: AgentConfig, embedding_service: EmbeddingService
) -> FeedbackRepository:
    if key == "in_memory":
        return InMemoryFeedbackRepository()
    if key == "json_file":
        return JsonHypothesisStore(cfg.backends.json_store_path, embedding_service)
    raise KeyError(f"unknown feedback_repository backend '{key}'")


def _build_understanding_engine(
    key: str, cfg: AgentConfig, llm_service: LLMService
) -> UnderstandingEngine:
    if key == "direct_llm":
        return DirectLLMUnderstandingEngine(llm_service, default_prompt_registry())
    if key == "deep_agent":
        return DeepAgentUnderstandingEngine(llm_service)
    raise KeyError(f"unknown understanding_engine backend '{key}'")


def _build_critic(key: str, llm_service: LLMService) -> Critic:
    if key == "checklist":
        return ChecklistCritic(llm_service, default_prompt_registry())
    if key == "strands":
        from hypothesis_agent.adapters.critique.strands_critic_orchestrator import (
            StrandsCriticOrchestrator,
        )

        return StrandsCriticOrchestrator()
    raise KeyError(f"unknown critic backend '{key}'")


def build_dependencies(config: AgentConfig | None = None) -> AgentDependencies:
    cfg = config or AgentConfig.load()
    prompts = default_prompt_registry()

    llm_service = _LLM_BACKENDS[cfg.backends.llm](cfg)
    embedding_service = _EMBEDDING_BACKENDS[cfg.backends.embedding](cfg)
    organization_repository = _ORGANIZATION_REPOSITORY_BACKENDS[cfg.backends.organization_repository](cfg)
    employee_repository = _EMPLOYEE_REPOSITORY_BACKENDS[cfg.backends.employee_repository](cfg)
    historical_memory_repository = _build_historical_memory_repository(
        cfg.backends.historical_memory_repository, cfg, embedding_service
    )
    feedback_repository = _build_feedback_repository(
        cfg.backends.feedback_repository, cfg, embedding_service
    )
    analysis_agent_gateway = _ANALYSIS_GATEWAY_BACKENDS[cfg.backends.analysis_agent_gateway](cfg)
    understanding_engine = _build_understanding_engine(cfg.backends.understanding_engine, cfg, llm_service)

    plugins = ReasoningPlugins(
        lenses=default_lens_registry(),
        evaluators=default_evaluator_registry(llm_service, prompts),
        critics=[_build_critic(key, llm_service) for key in cfg.backends.critics],
        search_heuristic=EntropyMaximizingHeuristic(
            exploration_floor=cfg.search.exploration_floor,
            mutation_probability=cfg.search.mutation_probability,
            discard_threshold=cfg.search.discard_threshold,
            rng=random.Random(cfg.search.random_seed) if cfg.search.random_seed is not None else None,
        ),
        memory_policy=SoftPriorPolicy(
            min_multiplier=cfg.feedback.min_multiplier,
            max_multiplier=cfg.feedback.max_multiplier,
            smoothing=cfg.feedback.smoothing,
        ),
    )

    return AgentDependencies(
        organization_repository=organization_repository,
        employee_repository=employee_repository,
        historical_memory_repository=historical_memory_repository,
        feedback_repository=feedback_repository,
        embedding_service=embedding_service,
        llm_service=llm_service,
        understanding_engine=understanding_engine,
        analysis_agent_gateway=analysis_agent_gateway,
        plugins=plugins,
        prompts=prompts,
        config=cfg,
    )
