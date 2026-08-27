import logging

from fastapi import APIRouter, HTTPException

from src.Agent.checkpointer import get_checkpointer
from src.Agent.memory.threads import delete_thread, get_thread_history, list_threads
from src.api.schemas.thread import (
    ThreadDeleteResponse,
    ThreadHistoryData,
    ThreadHistoryResponse,
    ThreadInfo,
    ThreadListData,
    ThreadListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["threads"])


@router.get("/threads", response_model=ThreadListResponse)
async def list_all_threads() -> ThreadListResponse:
    cp = get_checkpointer()
    threads = list_threads(cp)
    return ThreadListResponse(
        status="success",
        message=f"{len(threads)} thread(s) found",
        data=ThreadListData(threads=[ThreadInfo(**t) for t in threads]),
    )


@router.get("/threads/{thread_id}", response_model=ThreadHistoryResponse)
async def get_thread(thread_id: str) -> ThreadHistoryResponse:
    cp = get_checkpointer()
    messages = get_thread_history(cp, thread_id)
    if not messages:
        raise HTTPException(status_code=404, detail=f"Thread {thread_id!r} not found")
    return ThreadHistoryResponse(
        status="success",
        message=f"{len(messages)} message(s) in thread",
        data=ThreadHistoryData(
            thread_id=thread_id,
            messages=messages,
        ),
    )


@router.delete("/threads/{thread_id}", response_model=ThreadDeleteResponse)
async def delete_thread_endpoint(thread_id: str) -> ThreadDeleteResponse:
    cp = get_checkpointer()
    deleted = delete_thread(cp, thread_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Thread {thread_id!r} not found")
    return ThreadDeleteResponse(
        status="success",
        message=f"Thread {thread_id!r} deleted",
    )
