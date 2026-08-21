from langgraph.prebuilt import create_react_agent

from src.Agent.tools.retrieval_tool import search_products
from src.infrastructure.llm.factory import LLMFactory


def main():
    llm = LLMFactory.create()
    agent = create_react_agent(llm, tools=[search_products])

    questions = [
        "I want iphone 17",
    ]

    for q in questions:
        print(f"\nUser: {q}")
        print("-" * 50)

        result = agent.invoke({"messages": [("human", q)]})

        for msg in result["messages"]:
            if msg.type == "ai" and msg.content:
                print(f"Agent: {msg.content}")


if __name__ == "__main__":
    main()
