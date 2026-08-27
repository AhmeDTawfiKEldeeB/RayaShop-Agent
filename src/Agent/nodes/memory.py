import logging

from src.Agent.memory.summarise import summarize_if_needed
from src.Agent.state import AgentState
from src.Agent.trace import traceable

logger = logging.getLogger(__name__)


@traceable(name="memory_node", run_type="chain")
def memory_node(state: AgentState) -> dict:
    """Check message count and summarize old messages if threshold exceeded.

    Only writes to state["summary"].  Does not modify state["messages"] —
    the respond node reads the summary and slices messages itself.
    """
    messages = state.get("messages", [])
    existing_summary = state.get("summary")

    summary_text, _kept = summarize_if_needed(messages)

    if summary_text is None:
        return {}

    if existing_summary:
        summary_text = existing_summary + "\n\n" + summary_text

    logger.info(
        "memory_node: %d messages -> summary (%d chars)",
        len(messages), len(summary_text),
    )

    return {"summary": summary_text}
