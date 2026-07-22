from hypothesis_agent.contracts.hypothesis import (
    BusinessLens,
    CritiqueResult,
    DimensionScore,
    DownstreamHints,
    EvaluationScorecard,
    HypothesisCandidate,
    HypothesisPackage,
    Provenance,
    SearchDirective,
    SearchStatistics,
)
from hypothesis_agent.contracts.llm import LLMMessage, LLMRequest, LLMResponse
from hypothesis_agent.contracts.memory import (
    FeedbackRecord,
    FeedbackSummary,
    HistoricalHypothesisRecord,
    ReasoningTraceEntry,
)
from hypothesis_agent.contracts.organization import (
    AttributeField,
    EmployeeDataLandscape,
    OrganizationProfile,
    OrganizationUnderstanding,
)

# Resolve cross-module forward refs (hypothesis.py <-> memory.py) now that both
# modules are fully imported.
HypothesisPackage.model_rebuild()
HistoricalHypothesisRecord.model_rebuild()

__all__ = [
    "AttributeField",
    "BusinessLens",
    "CritiqueResult",
    "DimensionScore",
    "DownstreamHints",
    "EmployeeDataLandscape",
    "EvaluationScorecard",
    "FeedbackRecord",
    "FeedbackSummary",
    "HistoricalHypothesisRecord",
    "HypothesisCandidate",
    "HypothesisPackage",
    "LLMMessage",
    "LLMRequest",
    "LLMResponse",
    "OrganizationProfile",
    "OrganizationUnderstanding",
    "Provenance",
    "ReasoningTraceEntry",
    "SearchDirective",
    "SearchStatistics",
]
