from collections.abc import Generator
from functools import lru_cache

from src.Agent.checkpointer import get_checkpointer
from src.Agent.memory import build_graph


@lru_cache
def build_agent():
    return build_graph(checkpointer=get_checkpointer())


def ask(question: str, thread_id: str = "default") -> str:
    agent = build_agent()
    result = agent.invoke(
        {"messages": [("human", question)]},
        config={"configurable": {"thread_id": thread_id}},
    )
    return result["messages"][-1].content


def _stream_events(agent, question: str, thread_id: str) -> Generator[dict]:
    config = {"configurable": {"thread_id": thread_id}}
    in_think = False
    for mode, payload in agent.stream(
        {"messages": [("human", question)]},
        config,
        stream_mode=["updates", "messages"],
    ):
        if mode == "updates" and isinstance(payload, dict):
            for node_name, node_output in payload.items():
                if node_name == "retrieve":
                    results = node_output.get("search_results", []) if isinstance(node_output, dict) else []
                    if results:
                        yield {"type": "products", "products": results}
            continue

        if mode == "messages":
            chunk, meta = payload
            if isinstance(meta, dict) and meta.get("langgraph_node") in ("retrieve", "memory"):
                continue
            content = chunk.content
            if isinstance(content, str) and content:
                text = content
                if in_think:
                    end = text.find("</think>")
                    if end != -1:
                        in_think = False
                        text = text[end + 9:]
                    else:
                        continue
                start = text.find("<think>")
                if start != -1:
                    end = text.find("</think>", start)
                    if end != -1:
                        text = text[:start] + text[end + 9:]
                    else:
                        in_think = True
                        text = text[:start]
                if text.strip():
                    yield {"type": "token", "text": text}
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text" and block.get("text"):
                        text = block["text"]
                        if in_think:
                            end = text.find("</think>")
                            if end != -1:
                                in_think = False
                                text = text[end + 9:]
                            else:
                                continue
                        start = text.find("<think>")
                        if start != -1:
                            end = text.find("</think>", start)
                            if end != -1:
                                text = text[:start] + text[end + 9:]
                            else:
                                in_think = True
                                text = text[:start]
                        if text.strip():
                            yield {"type": "token", "text": text}


async def stream(question: str, thread_id: str = "default") -> Generator[dict]:
    import asyncio

    agent = build_agent()
    gen = _stream_events(agent, question, thread_id)
    loop = asyncio.get_running_loop()
    sentinel = object()
    while True:
        event = await loop.run_in_executor(None, next, gen, sentinel)
        if event is sentinel:
            break
        yield event


__all__ = ["ask", "build_agent", "stream"]
