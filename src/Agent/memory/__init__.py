from langgraph.checkpoint.base import BaseCheckpointSaver

from src.Agent.checkpointer import get_checkpointer
from src.Agent.graph import build_graph as _build_graph


def build_graph(checkpointer: BaseCheckpointSaver | None = None):
    return _build_graph(checkpointer=checkpointer or get_checkpointer())
