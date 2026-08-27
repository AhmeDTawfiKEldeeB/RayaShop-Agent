"""Unit tests for src.Agent.guardrails – check_input, is_greeting.

Greeting detection is the only deterministic guardrail.  Off-topic
detection is handled by the system prompt, not here.
"""

import pytest

from src.Agent.guardrails import (
    check_input,
    greeting_reply,
    is_greeting,
)

GREETINGS_EN = ["hi", "hello", "hey", "ok", "bye", "thanks"]
GREETINGS_AR = ["اهلا", "هلا", "السلام عليكم", "مرحبا", "شكرا", "ازيك"]


@pytest.mark.parametrize("text", GREETINGS_EN)
def test_greeting_english(text: str) -> None:
    assert is_greeting(text) is True
    reply = check_input(text)
    assert reply is not None
    assert "RayaShop" in reply


@pytest.mark.parametrize("text", GREETINGS_AR)
def test_greeting_arabic(text: str) -> None:
    assert is_greeting(text) is True
    reply = check_input(text)
    assert reply is not None


def test_greeting_with_punctuation() -> None:
    assert is_greeting("hello!") is True
    assert is_greeting("hi???") is True


def test_greeting_reply_language_en() -> None:
    assert "RayaShop" in greeting_reply("hello")


def test_greeting_reply_language_ar() -> None:
    reply = greeting_reply("اهلا")
    assert "ريا شوب" in reply or "رايا شوب" in reply


def test_greeting_multiword() -> None:
    assert is_greeting("thank you") is True
    assert is_greeting("السلام عليكم") is True


def test_non_greeting_not_caught() -> None:
    assert is_greeting("i want iphone 17") is False
    assert is_greeting("show me samsung phones") is False
    assert is_greeting("عايز موبايل سامسونج") is False


def test_check_input_returns_none_for_product_query() -> None:
    assert check_input("i want iphone 17") is None


def test_check_input_returns_none_for_arabic_product_query() -> None:
    assert check_input("عايز موبايل سامسونج") is None
