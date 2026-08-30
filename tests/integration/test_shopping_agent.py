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


def test_shopping_agent_retrieves_and_responds():
    agent = get_shopping_agent()
    
    query = "عاوز تلاجه من شركة فريش"
    print(f"\n--- Testing Shopping Agent with query: '{query}' ---")
    
    # Invoke the LangGraph agent
    result = agent.invoke({"messages": [("user", query)]})
    
    # Verify we got messages in the state
    messages = result.get("messages", [])
    assert len(messages) > 1, "Agent run did not generate any messages."
    
    print("\nConversation Trace:")
    for idx, msg in enumerate(messages, 1):
        role = msg.type
        content = msg.content
        print(f"\n{idx}. [{role.upper()}]:")
        
        # Print tool calls if any
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                print(f"   🔧 Tool Call: {tc['name']} with args: {tc['args']}")
                
        # Handle showing parsed JSON tool outputs cleanly
        if role == "tool":
            try:
                parsed_content = json.loads(content)
                print(f"   📦 Tool Output: Found {len(parsed_content)} products.")
            except Exception:
                print(f"   Content: {content}")
        else:
            print(f"   Content: {content}")
            
    # Final message assertions
    last_msg = messages[-1]
    assert last_msg.type == "ai", "The final response must be from the assistant."
    assert len(last_msg.content) > 0, "The assistant response must not be empty."


if __name__ == "__main__":
    test_shopping_agent_retrieves_and_responds()
