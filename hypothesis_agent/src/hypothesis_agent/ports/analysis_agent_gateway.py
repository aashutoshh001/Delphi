from abc import ABC, abstractmethod

from pydantic import BaseModel

from hypothesis_agent.contracts.hypothesis import HypothesisPackage


class AnalysisAgentAcknowledgement(BaseModel):
    accepted: bool
    downstream_reference: str | None = None
    message: str = ""


class AnalysisAgentGateway(ABC):
    """Forward-looking outbound port toward whatever consumes a
    HypothesisPackage next (Analysis Agent, Statistics Agent, ...). The
    Hypothesis Agent never knows what's on the other side — only that it can
    hand off a package and get an acknowledgement back. Out of scope for this
    implementation; `NoOpAnalysisAgentGateway` is the only adapter today."""

    @abstractmethod
    async def submit(self, package: HypothesisPackage) -> AnalysisAgentAcknowledgement: ...
