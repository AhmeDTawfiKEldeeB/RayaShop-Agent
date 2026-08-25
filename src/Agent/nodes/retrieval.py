import logging

from src.Agent.state import AgentState
from src.Agent.tools.retrieval_tool import search_products_raw
from src.Agent.utils import extract_message_content

logger = logging.getLogger(__name__)


def retrieval_node(state: AgentState) -> dict:
    """Run hybrid search on the user's latest message and store results."""
    last_msg = state["messages"][-1]
    query = extract_message_content(last_msg)

    results = search_products_raw(query)
    logger.info("retrieval_node: query=%r -> %d products", query, len(results))

    return {"search_results": results}
