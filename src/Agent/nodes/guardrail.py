import logging

from langchain_core.messages import AIMessage

from src.Agent.guardrails import check_input
from src.Agent.state import AgentState
from src.Agent.trace import traceable
from src.Agent.utils import extract_message_content

logger = logging.getLogger(__name__)


@traceable(name="guardrail_node", run_type="chain")
def guardrail_node(state: AgentState) -> dict:
    """Check input against guardrails. Block greetings and off-topic queries.

    Returns:
        ``{"messages": [AIMessage], "blocked": True}`` when the input is blocked.
        ``{"blocked": False}`` when the input should continue through the graph.

    ``blocked`` is always returned so that it resets any previous value
    persisted by the checkpointer (e.g. a greeting in the same thread).
    """
    messages = state.get("messages", [])
    if not messages:
        return {"blocked": False}

    last_msg = messages[-1]
    text = extract_message_content(last_msg)

    reply = check_input(text)
    if reply is not None:
        logger.info("guardrail_node: blocked input=%r", text[:80])
        return {"messages": [AIMessage(content=reply)], "blocked": True}

    return {"blocked": False}
