from pydantic import BaseModel, Field

from src.api.schemas.base import StandardResponse


class ThreadInfo(BaseModel):
    thread_id: str = Field(..., description="Unique conversation thread ID")
    created_at: str = Field(..., description="ISO timestamp of last activity")


class ThreadListData(BaseModel):
    threads: list[ThreadInfo]


class ThreadListResponse(StandardResponse[ThreadListData]):
    data: ThreadListData


class ThreadMessage(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message text")


class ThreadHistoryData(BaseModel):
    thread_id: str
    messages: list[ThreadMessage]


class ThreadHistoryResponse(StandardResponse[ThreadHistoryData]):
    data: ThreadHistoryData


class ThreadDeleteResponse(StandardResponse[None]):
    pass
