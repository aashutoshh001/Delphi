"""Builds the explicit LangGraph state graph for the hypothesis search loop
(§4/§13 of docs/ARCHITECTURE.md)."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from hypothesis_agent.reasoning.dependencies import AgentDependencies
from hypothesis_agent.reasoning.nodes import (
    make_continue_decision_node,
    make_critique_node,
    make_estimate_business_value_node,
    make_estimate_novelty_node,
    make_finalize_node,
    make_generate_candidate_node,
    make_generate_search_direction_node,
    make_improve_node,
    make_observe_node,
    make_understand_organization_node,
    route_after_continue_decision,
)
from hypothesis_agent.reasoning.state import HypothesisSearchState


def build_hypothesis_graph(deps: AgentDependencies) -> CompiledStateGraph:
    builder = StateGraph(HypothesisSearchState)

    builder.add_node("observe", make_observe_node(deps))
    builder.add_node("understand_organization", make_understand_organization_node(deps))
    builder.add_node("generate_search_direction", make_generate_search_direction_node(deps))
    builder.add_node("generate_candidate", make_generate_candidate_node(deps))
    builder.add_node("critique", make_critique_node(deps))
    builder.add_node("estimate_business_value", make_estimate_business_value_node(deps))
    builder.add_node("estimate_novelty", make_estimate_novelty_node(deps))
    builder.add_node("improve", make_improve_node(deps))
    builder.add_node("continue_decision", make_continue_decision_node(deps))
    builder.add_node("finalize", make_finalize_node(deps))

    builder.add_edge(START, "observe")
    builder.add_edge("observe", "understand_organization")
    builder.add_edge("understand_organization", "generate_search_direction")
    builder.add_edge("generate_search_direction", "generate_candidate")
    builder.add_edge("generate_candidate", "critique")
    builder.add_edge("critique", "estimate_business_value")
    builder.add_edge("estimate_business_value", "estimate_novelty")
    builder.add_edge("estimate_novelty", "improve")
    builder.add_edge("improve", "continue_decision")
    builder.add_conditional_edges(
        "continue_decision",
        route_after_continue_decision,
        {"continue": "generate_search_direction", "finalize": "finalize"},
    )
    builder.add_edge("finalize", END)

    return builder.compile()
