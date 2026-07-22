"""Everything a compiled hypothesis graph needs, expressed purely in terms of
ports and plugins. Lives in `reasoning/` (not `di/`) so the reasoning layer's
import boundary — contracts + ports only, never adapters — includes this
bundle's own definition. `di/container.py` is the only place that imports
adapters and constructs one of these."""

from __future__ import annotations

from dataclasses import dataclass

from hypothesis_agent.config.settings import AgentConfig
from hypothesis_agent.plugins import ReasoningPlugins
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
from hypothesis_agent.prompts.registry import PromptRegistry


@dataclass
class AgentDependencies:
    organization_repository: OrganizationRepository
    employee_repository: EmployeeRepository
    historical_memory_repository: HistoricalMemoryRepository
    feedback_repository: FeedbackRepository
    embedding_service: EmbeddingService
    llm_service: LLMService
    understanding_engine: UnderstandingEngine
    analysis_agent_gateway: AnalysisAgentGateway
    plugins: ReasoningPlugins
    prompts: PromptRegistry
    config: AgentConfig
