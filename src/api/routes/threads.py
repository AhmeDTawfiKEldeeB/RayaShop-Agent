import logging
import uuid
import psycopg
from fastapi import APIRouter
from src.api.schemas.thread import ThreadInfo, ThreadItem, ThreadListResponse, ThreadMessagesResponse, MessageInfo
from src.Agent.checkpointer import get_checkpointer
from src.config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/threads", tags=["Threads"])


@router.post("", response_model=ThreadInfo)
async def create_thread():
    thread_id = str(uuid.uuid4())
    return ThreadInfo(thread_id=thread_id)


@router.get("", response_model=ThreadListResponse)
async def list_threads():
    """Retrieve all historical chat sessions from PostgreSQL."""
    checkpointer = get_checkpointer()
    conn_info = f"postgresql://{settings.postgres.user}:{settings.postgres.password}@{settings.postgres.host}:{settings.postgres.port}/{settings.postgres.database}"
    
    threads = []
    try:
        with psycopg.connect(conn_info) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT thread_id, MAX(checkpoint_id) as last_cp
                    FROM checkpoints
                    WHERE checkpoint_ns = ''
                    GROUP BY thread_id
                    ORDER BY last_cp DESC;
                """)
                rows = cur.fetchall()
                
        for thread_id, _ in rows:
            config = {"configurable": {"thread_id": thread_id}}
            tuple_state = checkpointer.get_tuple(config)
            title = f"Session {thread_id[:8]}"
            if tuple_state and tuple_state.checkpoint:
                messages = tuple_state.checkpoint.get("channel_values", {}).get("messages", [])
                for m in messages:
                    msg_type = getattr(m, "type", None) or getattr(m, "role", None)
                    if msg_type in ["human", "user"] and m.content:
                        clean_text = m.content.strip()
                        title = clean_text[:30] + ("..." if len(clean_text) > 30 else "")
                        break
            threads.append(ThreadItem(thread_id=thread_id, title=title))
    except Exception as exc:
        logger.exception("Error querying threads from PostgreSQL: %s", exc)
        
    return ThreadListResponse(threads=threads)


@router.get("/{thread_id}/messages", response_model=ThreadMessagesResponse)
async def get_thread_messages(thread_id: str):
    """Retrieve stored conversation messages for a specific thread from PostgreSQL."""
    checkpointer = get_checkpointer()
    config = {"configurable": {"thread_id": thread_id}}
    tuple_state = checkpointer.get_tuple(config)
    
    messages = []
    if tuple_state and tuple_state.checkpoint:
        channel_messages = tuple_state.checkpoint.get("channel_values", {}).get("messages", [])
        for msg in channel_messages:
            msg_type = getattr(msg, "type", None) or getattr(msg, "role", None)
            if msg_type in ["human", "user", "ai", "assistant"]:
                role = "user" if msg_type in ["human", "user"] else "assistant"
                content = getattr(msg, "content", "")
                if content and isinstance(content, str) and content.strip():
                    messages.append(MessageInfo(role=role, content=content))
                
    return ThreadMessagesResponse(thread_id=thread_id, messages=messages)
