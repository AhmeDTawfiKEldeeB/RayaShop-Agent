from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from src.Agent.nodes import (
    guardrail_node,
    memory_node,
    respond_node,
    retrieval_node,
)
from src.Agent.state import AgentState


def _route_after_guardrail(state: AgentState) -> str:
    """Route to END when blocked, otherwise continue to memory."""
    if state.get("blocked"):
        return "blocked"
    return "continue"


def build_graph(checkpointer: BaseCheckpointSaver | None = None):
    graph = StateGraph(AgentState)

    graph.add_node("guardrail", guardrail_node)
    graph.add_node("memory", memory_node)
    graph.add_node("retrieve", retrieval_node)
    graph.add_node("respond", respond_node)

    graph.add_edge(START, "guardrail")
    graph.add_conditional_edges(
        "guardrail",
        _route_after_guardrail,
        {"blocked": END, "continue": "memory"},
    )
    graph.add_edge("memory", "retrieve")
    graph.add_edge("retrieve", "respond")
    graph.add_edge("respond", END)

    return graph.compile(checkpointer=checkpointer)
