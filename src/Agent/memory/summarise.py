import logging

from langchain_core.messages import HumanMessage

from src.Agent.utils import extract_message_content, message_role

logger = logging.getLogger(__name__)

SUMMARY_THRESHOLD = 10
KEEP_RECENT = 6

SUMMARIZE_PROMPT = """\
Summarise this conversation between a user and a shopping assistant. \
Keep it short — a few bullet points. \
Include: products discussed, prices mentioned, user preferences (brand, budget), \
and any decisions made. \
Preserve useful product-search details from tool results. \
Do NOT include greetings, filler, or irrelevant conversation."""

_summarizer = None


def _get_summarizer():
    global _summarizer
    if _summarizer is None:
        from src.infrastructure.llm.factory import LLMFactory
        _summarizer = LLMFactory.create()
    return _summarizer


def summarize_if_needed(
    messages: list,
    threshold: int = SUMMARY_THRESHOLD,
    keep_recent: int = KEEP_RECENT,
) -> tuple[str | None, list]:
    """Summarize old messages when count exceeds *threshold*.

    Returns ``(summary_text | None, kept_messages)``.
    *summary_text* is the compressed history string.
    *kept_messages* are the most recent messages kept verbatim.
    """
    if len(messages) <= threshold:
        return None, list(messages)

    to_summarize = messages[:-keep_recent]
    kept = messages[-keep_recent:]

    logger.info(
        "summarize_if_needed: %d messages total, summarising %d, keeping %d",
        len(messages), len(to_summarize), len(kept),
    )

    summary_text = _call_summarizer(to_summarize)
    return summary_text, kept


def _call_summarizer(messages: list) -> str:
    llm = _get_summarizer()
    formatted = []
    for msg in messages:
        role = message_role(msg)
        content = extract_message_content(msg)
        formatted.append(f"{role}: {content}")

    prompt = SUMMARIZE_PROMPT + "\n\n" + "\n".join(formatted)
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content
