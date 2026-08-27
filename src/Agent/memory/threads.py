import logging
from datetime import UTC, datetime

from langgraph.checkpoint.postgres import PostgresSaver

from src.Agent.utils import extract_message_content, message_role

logger = logging.getLogger(__name__)


def list_threads(checkpointer: PostgresSaver) -> list[dict]:
    """Return all threads with their last activity timestamp."""
    seen: dict[str, dict] = {}
    for tpl in checkpointer.list(None):
        tid = tpl.config["configurable"]["thread_id"]
        created = tpl.metadata.get("created_at") if tpl.metadata else None
        if tid not in seen or (created and created > seen[tid]["created_at"]):
            seen[tid] = {
                "thread_id": tid,
                "created_at": created or datetime.now(UTC).isoformat(),
            }
    return sorted(seen.values(), key=lambda t: t["created_at"], reverse=True)


def get_thread_history(
    checkpointer: PostgresSaver, thread_id: str,
) -> list[dict]:
    """Return the conversation messages for *thread_id*."""
    config = {"configurable": {"thread_id": thread_id}}
    msgs: list[dict] = []
    for tpl in checkpointer.list(config):
        state = tpl.checkpoint.get("channel_values", {})
        for msg in state.get("messages", []):
            role = message_role(msg)
            if role in ("system", "tool"):
                continue
            msgs.append({"role": role, "content": extract_message_content(msg)})
    return msgs


def delete_thread(checkpointer: PostgresSaver, thread_id: str) -> bool:
    """Delete all checkpoints for *thread_id*.  Returns True if existed."""
    config = {"configurable": {"thread_id": thread_id}}
    existing = list(checkpointer.list(config, limit=1))
    if not existing:
        return False
    checkpointer.delete_thread(thread_id)
    logger.info("Deleted thread %s", thread_id)
    return True
