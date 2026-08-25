"""Input guardrails for the RayaShop agent.

Central place for input classification rules (greetings, etc.)
so they are applied consistently at the agent entry point instead of
inside individual tools.
"""

import re

GREETINGS = {
    "hi", "hello", "hey", "ahla", "ahlan", "hola", "salam", "marhaba",
    "thanks", "thank you", "thanks!", "ok", "okay", "bye", "goodbye",
    "مرحبا", "اهلا", "اهلاين", "هلا", "السلام عليكم", "سلام",
    "صباح الخير", "مساء الخير", "ازيك", "عامل ايه", "شكرا", "متشكر",
    "تمام", "خلاص", "باي",
}

_ARABIC_RE = re.compile(r"[\u0600-\u06FF]")

_GREETING_REPLY_AR = "أهلاً بك في مساعد رايا شوب ! 👋 ازاي اقدر اساعدك؟."
_GREETING_REPLY_EN = "Hello! Welcome to RayaShop Agent 👋 How can I help you? "


def is_greeting(text: str) -> bool:
    """True when the input is pure small talk (no product intent)."""
    normalized = re.sub(r"[^\w\s\u0600-\u06FF]", "", text.strip().lower()).strip()
    return normalized in GREETINGS


def greeting_reply(text: str) -> str:
    """Canned reply for greetings, in the user's language."""
    if _ARABIC_RE.search(text):
        return _GREETING_REPLY_AR
    return _GREETING_REPLY_EN


def check_input(text: str) -> str | None:
    """Single entry point for input guardrails.

    Returns a canned reply when the input is a greeting,
    or ``None`` when the input should be forwarded to the agent.
    """
    if is_greeting(text):
        return greeting_reply(text)
    return None
