import logging
import re

from langchain_core.messages import SystemMessage

from src.Agent.memory.summarise import KEEP_RECENT
from src.Agent.prompts import SEARCH_RESULTS_TEMPLATE, SYSTEM_PROMPT
from src.Agent.state import AgentState
from src.Agent.trace import traceable
from src.infrastructure.llm.factory import LLMFactory

logger = logging.getLogger(__name__)

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


def _strip_think(text: str) -> str:
    return _THINK_RE.sub("", text).strip()


def _format_products(products: list[dict]) -> str:
    """Format a list of product dicts into a readable block for the LLM."""
    if not products:
        return "No products found."
    lines = []
    for p in products:
        price = f"{p['price']:,} EGP" if p.get("price") else "N/A"
        old = f" (was {p['old_price']:,})" if p.get("old_price") else ""
        stock = p.get("stock_status", "")
        lines.append(f"- {p['name']} — {price}{old} | {stock}")
    return "\n".join(lines)


@traceable(name="respond_node", run_type="llm")
def respond_node(state: AgentState) -> dict:
    """Call the LLM with conversation history + search results context.

    Context order:
        System Prompt + Search Results + Summary (if any) + Recent Messages
    """
    llm = LLMFactory.create()

    search_results = state.get("search_results", [])
    results_block = _format_products(search_results)
    search_context = SEARCH_RESULTS_TEMPLATE.format(results=results_block)

    summary = state.get("summary")
    messages = list(state.get("messages", []))

    recent = messages[-KEEP_RECENT:] if summary else messages

    context = [SystemMessage(content=SYSTEM_PROMPT + "\n\n" + search_context)]
    if summary:
        context.append(SystemMessage(content=f"Conversation summary:\n{summary}"))
    context.extend(recent)

    response = llm.invoke(context)

    clean_content = _strip_think(response.content)
    response.content = clean_content

    logger.info("respond_node: generated %d chars", len(clean_content))
    return {"messages": [response]}
