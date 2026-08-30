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
            if isinstance(msg.content, str):
                final_ai_msg = msg.content
            elif isinstance(msg.content, list):
                text_parts = []
                for part in msg.content:
                    if isinstance(part, dict) and "text" in part:
                        text_parts.append(part["text"])
                    elif isinstance(part, str):
                        text_parts.append(part)
                final_ai_msg = "\n".join(text_parts) if text_parts else str(msg.content)
            elif isinstance(msg.content, dict) and "text" in msg.content:
                final_ai_msg = msg.content["text"]
            else:
                final_ai_msg = str(msg.content)
            break
            
    products = []
    # Find products from the MOST RECENT tool call
    for msg in reversed(result.get("messages", [])):
        if msg.type == "tool":
            try:
                content = msg.content
                if isinstance(content, str):
                    data = json.loads(content)
                else:
                    data = content
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

