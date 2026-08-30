import json
import uuid
from fastapi import APIRouter
from src.api.schemas.chat import ChatRequest, ChatResponse, ChatProduct
from src.Agent.shopping_agent import get_shopping_agent

router = APIRouter(prefix="/api/v1/chat", tags=["Chat"])

@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    thread_id = request.thread_id or str(uuid.uuid4())
    
    agent = get_shopping_agent()
    result = agent.invoke(
        {"messages": [("user", request.message)]}, 
        config={"configurable": {"thread_id": thread_id}}
    )
    
    final_ai_msg = ""
    for msg in reversed(result.get("messages", [])):
        if msg.type == "ai":
            final_ai_msg = msg.content
            break
            
    products = []
    # Find products from the MOST RECENT tool call
    for msg in reversed(result.get("messages", [])):
        if msg.type == "tool":
            try:
                data = json.loads(msg.content)
                if isinstance(data, list) and len(data) > 0:
                    tool_products = []
                    for item in data:
                        if isinstance(item, dict) and 'name' in item and 'price' in item:
                            tool_products.append(ChatProduct(**item))
                    if tool_products:
                        products = tool_products
                        break  # Take only the products from the latest search
            except Exception:
                pass
                
    return ChatResponse(
        thread_id=thread_id,
        response=final_ai_msg,
        products=products
    )
