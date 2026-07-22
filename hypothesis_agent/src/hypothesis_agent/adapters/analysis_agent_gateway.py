from __future__ import annotations

from hypothesis_agent.contracts.hypothesis import HypothesisPackage
from hypothesis_agent.ports.analysis_agent_gateway import (
    AnalysisAgentAcknowledgement,
    AnalysisAgentGateway,
)


class NoOpAnalysisAgentGateway(AnalysisAgentGateway):
    """Placeholder for the not-yet-built downstream Analysis Agent. Accepts
    every package without forwarding it anywhere — swap for a real client
    once a downstream agent exists, with zero change to the reasoning engine."""

    async def submit(self, package: HypothesisPackage) -> AnalysisAgentAcknowledgement:
        return AnalysisAgentAcknowledgement(
            accepted=True,
            downstream_reference=None,
            message="No downstream Analysis Agent is configured yet; package was not forwarded.",
        )
