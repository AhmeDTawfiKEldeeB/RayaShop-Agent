import logging
import re

from langchain_core.messages import HumanMessage

from src.Agent.state import AgentState
from src.Agent.tools.retrieval_tool import search_products_raw
from src.Agent.trace import traceable
from src.Agent.utils import extract_message_content
from src.infrastructure.llm.factory import LLMFactory

logger = logging.getLogger(__name__)

_ARABIC_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]+")
_translate_llm = None

# Question/follow-up signals.  When the user is asking about a product that
# was already retrieved (colour, warranty, price, stock, ...) we should NOT
# run a fresh search that would replace the shown images.
_FOLLOWUP_SIGNALS = [
    "color",
    "colour",
    "warranty",
    "price",
    "stock",
    "available",
    "availability",
    "size",
    "inch",
    "ram",
    "storage",
    "memory",
    "guarantee",
    "model",
    "specification",
    "specs",
    "difference",
    "which",
    "compare",
    "compare",
    "what about",
    "how about",
    "is it",
    "are there",
    "does it",
    "do you have",
    "بالظبط",
    "كام",
    "إيه",
    "ايه",
    "لونه",
    "مواصفات",
    "فرق",
    "متوفر",
    "ضمان",
    "سعر",
    "ليه",
    "ازاي",
    "يعني",
]

# Product-type tokens: presence in the user message indicates a NEW
# product-search intent (so we should search), not a follow-up.
_PRODUCT_TYPE_SIGNALS = [
    "laptop",
    "notebook",
    "phone",
    "mobile",
    "smartphone",
    "tablet",
    "television",
    "tv",
    "monitor",
    "air conditioner",
    "conditioner",
    "washing machine",
    "washer",
    "refrigerator",
    "fridge",
    "microwave",
    "vacuum",
    "headphone",
    "headset",
    "earbud",
    "speaker",
    "camera",
    "printer",
    "router",
    "blender",
    "mixer",
    "kettle",
    "fryer",
    "oven",
    "coffee",
    "juicer",
    "محمول",
    "لابتوب",
    "تليفون",
    "موبايل",
    "تلفزيون",
    "تكييف",
    "غسالة",
    "مكنسة",
    "سماعة",
    "كاميرا",
]


def _is_followup_question(query: str) -> bool:
    """True when the message is a follow-up about already-shown products."""
    q = query.lower()
    has_followup = any(sig in q for sig in _FOLLOWUP_SIGNALS)
    has_product_type = any(sig in q for sig in _PRODUCT_TYPE_SIGNALS)
    # A follow-up asks a question about existing items WITHOUT introducing a
    # brand-new product category to search.
    return has_followup and not has_product_type


def _get_translate_llm():
    global _translate_llm
    if _translate_llm is None:
        _translate_llm = LLMFactory.create("groq")
    return _translate_llm


def _translate_query(text: str) -> str:
    """Translate an Arabic product query to English search keywords."""
    if not _ARABIC_RE.search(text):
        return text
    try:
        llm = _get_translate_llm()
        resp = llm.invoke([
            HumanMessage(content=(
                "/no_think\n"
                "Translate this Arabic product search query to short English "
                "keywords for an e-commerce product search. Return ONLY the "
                "translated keywords, nothing else.\n\n"
                f"Query: {text}"
            ))
        ])
        translated = resp.content.strip()
        if translated:
            logger.info("Translated %r -> %r", text, translated)
            return translated
    except Exception:
        logger.warning("Translation failed for %r", text, exc_info=True)
    return text


def _get_latest_user_message(
    state: AgentState,
):
    """
    Return the latest HumanMessage from the conversation.

    The retrieval node must search using the user's latest
    actual request, not simply the last message in the state.
    """

    for message in reversed(
        state["messages"]
    ):

        if getattr(
            message,
            "type",
            None,
        ) == "human":

            return message

    return None


@traceable(name="retrieval_node", run_type="retriever")
def retrieval_node(
    state: AgentState,
) -> dict:
    """
    Execute product retrieval for the current user request.

    Responsibilities:
    - extract the latest user query
    - call the existing retrieval capability
    - store results in AgentState

    This node does not:
    - perform guardrails
    - call the LLM
    - format the final answer
    - implement Weaviate logic
    """

    message = _get_latest_user_message(
        state
    )

    if message is None:

        logger.warning(
            "retrieval_node: no human message found"
        )

        return {
            "search_results": []
        }

    query = extract_message_content(
        message
    ).strip()

    if not query:

        logger.warning(
            "retrieval_node: empty user query"
        )

        return {
            "search_results": []
        }

    existing = state.get("search_results") or []

    # Follow-up questions about already-shown products (colour, price,
    # warranty, ...) must NOT re-run a search — keep the previous results
    # so the UI panel isn't replaced with a new set of images.
    if _is_followup_question(query) and existing:
        logger.info(
            "retrieval_node: follow-up question %r — reusing %d products",
            query, len(existing),
        )
        return {
            "search_results": existing,
        }

    search_query = _translate_query(query)

    results = search_products_raw(
        query=search_query,
        limit=7,
    )

    logger.info(
        "retrieval_node: query=%r -> %d products",
        query,
        len(results),
    )

    return {
        "search_results": results
    }