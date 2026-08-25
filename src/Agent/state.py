from typing import Annotated

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from langgraph.managed import RemainingSteps
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """State of the RayaShop agent graph.

    Attributes:
        messages: Conversation history (user, assistant, tool messages).
                  New messages are appended via the add_messages reducer.
        search_results: Products returned by the latest search_products call.
                        Overwritten on each search (last write wins).
        remaining_steps: LangGraph recursion budget for the ReAct loop.
    """

    messages: Annotated[list[AnyMessage], add_messages]
    search_results: list[dict]
    remaining_steps: RemainingSteps
