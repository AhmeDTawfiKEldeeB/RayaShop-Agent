import json
import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

import src.Agent as agent_module
from src.api.schemas.chat import ChatData, ChatRequest, ChatResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    reply = agent_module.ask(request.message, thread_id=request.thread_id)
    if not isinstance(reply, str):
        reply = "".join(
            block.get("text", "") for block in reply if isinstance(block, dict)
        )
    return ChatResponse(
        status="success",
        message="Reply generated",
        data=ChatData(thread_id=request.thread_id, reply=reply),
    )


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def _event_stream(message: str, thread_id: str):
    try:
        async for event in agent_module.stream(message, thread_id=thread_id):
            yield _sse(event)
    except Exception as exc:
        logger.exception("Streaming failed for thread=%s", thread_id)
        yield _sse({"type": "error", "text": str(exc)})
    yield _sse({"type": "done"})


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    return StreamingResponse(
        _event_stream(request.message, request.thread_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
