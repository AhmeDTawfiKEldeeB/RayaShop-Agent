"""Shared low-level helpers used across multiple Agent modules."""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage


def extract_message_content(msg) -> str:
    """Return the text content of any LangChain message type.

    Handles:
    - Standard messages with a ``content`` attribute (str or list of blocks).
    - Fallback to ``str(msg)`` for unknown message shapes.
    - List-of-blocks content (multi-modal payloads) joined into a single string.
    """
    raw = msg.content if hasattr(msg, "content") else str(msg)
    if isinstance(raw, list):
        return " ".join(
            block.get("text", "") for block in raw if isinstance(block, dict)
        )
    return raw


def message_role(msg) -> str:
    """Return a human-readable role string for *msg*.

    Normalises to ``"user"`` / ``"assistant"`` / ``"system"`` / ``"tool"``.
    Falls back to the class name for unknown message types.
    """
    if isinstance(msg, HumanMessage):
        return "user"
    if isinstance(msg, AIMessage):
        return "assistant"
    if isinstance(msg, SystemMessage):
        return "system"
    if isinstance(msg, ToolMessage):
        return "tool"
    return type(msg).__name__
