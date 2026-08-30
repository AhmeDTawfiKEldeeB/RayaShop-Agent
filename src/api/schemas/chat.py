from pydantic import BaseModel

class ChatRequest(BaseModel):
    thread_id: str | None = None
    message: str

class ChatProduct(BaseModel):
    id: int | str | None = None
    name: str = ""
    brand: str = ""
    price: float = 0
    old_price: float | None = None
    stock_status: str = ""
    url: str = ""
    thumbnail: str | None = None
    score: float = 0

class ChatResponse(BaseModel):
    thread_id: str
    response: str
    products: list[ChatProduct] = []
