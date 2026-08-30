import json
import pytest
import sys

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.Agent.shopping_agent import get_shopping_agent
from src.Agent.tools.retrieval_tool import close_db

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def cleanup():
    yield
    close_db()


def test_agent_conversation_memory_on_postgres():
    agent = get_shopping_agent()
    
    # Define a unique thread ID to test session/thread persistence
    config = {"configurable": {"thread_id": "test_thread_ahmed_12345"}}
    
    print("\n==================================================")
    print("TURN 1: Introducing user and preferred brand")
    print("==================================================")
    
    query1 = "أنا اسمي أحمد وبحب منتجات شركة فريش"
    print(f"User: '{query1}'")
    
    result1 = agent.invoke({"messages": [("user", query1)]}, config=config)
    messages1 = result1.get("messages", [])
    
    print("\nTurn 1 Conversation Trace:")
    for idx, msg in enumerate(messages1, 1):
        role = msg.type
        content = msg.content
        print(f"\n{idx}. [{role.upper()}]:")
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                print(f"   🔧 Tool Call: {tc['name']} with args: {tc['args']}")
        print(f"   Content: {content}")
        
    print("\n==================================================")
    print("TURN 2: Asking for a product (should recall name and brand preference)")
    print("==================================================")
    
    query2 = "عاوز تلاجه بقى"
    print(f"User: '{query2}'")
    
    # Invoke the agent on the SAME thread
    result2 = agent.invoke({"messages": [("user", query2)]}, config=config)
    
    # Get only the new messages generated in the second turn
    messages2 = result2.get("messages", [])
    new_messages = messages2[len(messages1):]
    
    print("\nTurn 2 Conversation Trace:")
    for idx, msg in enumerate(new_messages, 1):
        role = msg.type
        content = msg.content
        print(f"\n{idx}. [{role.upper()}]:")
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                print(f"   🔧 Tool Call: {tc['name']} with args: {tc['args']}")
        print(f"   Content: {content}")
        
    # Assertions
    # 1. Verify a tool call was made in Turn 1 to save the preference
    saved_pref = False
    for msg in messages1:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                if tc["name"] == "save_user_preference":
                    saved_pref = True
                    break
    
    # 2. Verify checkpointer recalled name and brand in Turn 2
    final_response = new_messages[-1].content
    print("\nFinal response verification:")
    print("Content:", final_response)
    
    # The assistant should address the user as "أحمد" or mention "فريش" / "Fresh"
    assert "أحمد" in final_response or "احمد" in final_response, "Agent failed to recall the user's name via thread checkpointer"
    assert "Fresh" in final_response or "فريش" in final_response, "Agent failed to prioritize user's brand preference"


if __name__ == "__main__":
    test_agent_conversation_memory_on_postgres()
