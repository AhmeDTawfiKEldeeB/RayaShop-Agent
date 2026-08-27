from typing import Annotated

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """State of the RayaShop agent graph.

    Attributes:
        messages: Conversation history (user, assistant, tool messages).
                  New messages are appended via the add_messages reducer.
        summary: Compressed history of older messages. None until
                 summarization is triggered by exceeding the message threshold.
        search_results: Products returned by the latest search_products call.
                        Overwritten on each search (last write wins).
        blocked: Set to True by the guardrail node when the input is a
                 greeting or off-topic query. Used by the graph router.
    """

    messages: Annotated[list[AnyMessage], add_messages]
    summary: str | None
    search_results: list[dict]
    blocked: bool | None
