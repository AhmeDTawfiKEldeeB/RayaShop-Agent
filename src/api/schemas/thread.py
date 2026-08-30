from pydantic import BaseModel

class ThreadCreate(BaseModel):
    pass

class ThreadInfo(BaseModel):
    thread_id: str

class ThreadItem(BaseModel):
    thread_id: str
    title: str

class ThreadListResponse(BaseModel):
    threads: list[ThreadItem]

class MessageInfo(BaseModel):
    role: str
    content: str

class ThreadMessagesResponse(BaseModel):
    thread_id: str
    messages: list[MessageInfo]
