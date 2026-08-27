from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from src.api.schemas.base import StandardResponse


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User message to the assistant")
    thread_id: str = Field(default="default", description="Conversation thread ID for memory")
    stream: bool = Field(default=False, description="Return response as server-sent events")


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ChatData(BaseModel):
    thread_id: str = Field(..., description="Thread ID used for this conversation")
    reply: str = Field(..., description="Assistant reply text")


class ChatResponse(StandardResponse[ChatData]):
    data: ChatData


class StreamEvent(BaseModel):
    type: Literal["tool", "token", "done", "error"]
    name: str | None = Field(None, description="Tool name, when type == 'tool'")
    text: str | None = Field(None, description="Token text, when type == 'token'")
