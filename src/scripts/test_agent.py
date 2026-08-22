import sys

from langgraph.prebuilt import create_react_agent

from src.Agent.tools.retrieval_tool import search_products
from src.infrastructure.llm.factory import LLMFactory

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    llm = LLMFactory.create()
    agent = create_react_agent(llm, tools=[search_products])

    questions = [
        "I want Refurbished Apple iPhone 16 Pro Max Single",
        "SONY WH-1000XM5 price",
        "wireless gaming mouse rgb",
    ]

    for q in questions:
        print(f"\nUser: {q}")
        print("-" * 50)

        result = agent.invoke({"messages": [("human", q)]})

        for msg in result["messages"]:
            if msg.type == "ai":
                if isinstance(msg.content, str) and msg.content:
                    print(f"Agent: {msg.content}")
                elif isinstance(msg.content, list):
                    for block in msg.content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            print(f"Agent: {block['text']}")


if __name__ == "__main__":
    main()
