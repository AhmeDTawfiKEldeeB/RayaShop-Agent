import json
from collections.abc import Generator
from functools import lru_cache

from src.Agent.guardrails import check_input
from src.Agent.memory import build_graph
from src.Agent.memory.checkpoint import get_checkpointer


@lru_cache
def build_agent():
    return build_graph(checkpointer=get_checkpointer())


def ask(question: str, thread_id: str = "default") -> str:
    reply = check_input(question)
    if reply is not None:
        return reply
    agent = build_agent()
    result = agent.invoke(
        {"messages": [("human", question)]},
        config={"configurable": {"thread_id": thread_id}},
    )
    return result["messages"][-1].content


def _parse_products(content) -> tuple[bool, list[dict]]:
    if isinstance(content, list):
        content = "".join(str(part) for part in content)
    if not isinstance(content, str) or not content.strip().startswith("["):
        return False, []
    try:
        data = json.loads(content)
    except ValueError:
        return False, []
    if not isinstance(data, list):
        return False, []
    return True, [p for p in data if isinstance(p, dict) and "name" in p]


def _stream_events(agent, question: str, thread_id: str) -> Generator[dict]:
    reply = check_input(question)
    if reply is not None:
        yield {"type": "token", "text": reply}
        return

    config = {"configurable": {"thread_id": thread_id}}
    for mode, payload in agent.stream(
        {"messages": [("human", question)]},
        config,
        stream_mode=["updates", "messages"],
    ):
        if mode == "updates":
            if isinstance(payload, dict):
                for node_output in payload.values():
                    messages = node_output.get("messages", []) if isinstance(node_output, dict) else []
                    for msg in messages:
                        tool_calls = getattr(msg, "tool_calls", None)
                        if tool_calls:
                            yield {"type": "tool", "name": tool_calls[0]["name"]}
                            continue
                        if getattr(msg, "type", "") == "tool":
                            ok, products = _parse_products(getattr(msg, "content", None))
                            if ok:
                                yield {"type": "products", "products": products}
            continue

        chunk, meta = payload
        if isinstance(meta, dict) and meta.get("langgraph_node") == "tools":
            continue
        content = chunk.content
        if isinstance(content, str) and content:
            yield {"type": "token", "text": content}
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text" and block.get("text"):
                    yield {"type": "token", "text": block["text"]}


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
