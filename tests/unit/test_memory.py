"""Unit tests for src.Agent.memory.summarise — threshold logic and message handling."""

from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from src.Agent.memory.summarise import summarize_if_needed


def _make_messages(n: int) -> list:
    msgs = []
    for i in range(n):
        if i % 2 == 0:
            msgs.append(HumanMessage(content=f"user msg {i}"))
        else:
            msgs.append(AIMessage(content=f"assistant msg {i}"))
    return msgs


# --- threshold logic (no LLM needed) ---


def test_below_threshold_returns_no_summary() -> None:
    msgs = _make_messages(9)
    summary, kept = summarize_if_needed(msgs, threshold=10, keep_recent=6)
    assert summary is None
    assert kept == msgs


def test_at_threshold_returns_no_summary() -> None:
    msgs = _make_messages(10)
    summary, kept = summarize_if_needed(msgs, threshold=10, keep_recent=6)
    assert summary is None
    assert kept == msgs


def test_above_threshold_triggers_summary() -> None:
    msgs = _make_messages(12)
    with patch("src.Agent.memory.summarise._call_summarizer", return_value="summary text"):
        summary, kept = summarize_if_needed(msgs, threshold=10, keep_recent=6)
    assert summary == "summary text"
    assert len(kept) == 6
    assert kept[0].content == "user msg 6"


def test_kept_messages_are_the_most_recent() -> None:
    msgs = _make_messages(15)
    with patch("src.Agent.memory.summarise._call_summarizer", return_value="s"):
        _, kept = summarize_if_needed(msgs, threshold=10, keep_recent=6)
    assert [m.content for m in kept] == [f"{'user' if i % 2 == 0 else 'assistant'} msg {i}" for i in range(9, 15)]


def test_summarizer_receives_old_messages_only() -> None:
    msgs = _make_messages(12)
    with patch("src.Agent.memory.summarise._call_summarizer", return_value="s") as mock_sum:
        summarize_if_needed(msgs, threshold=10, keep_recent=6)
    old = mock_sum.call_args[0][0]
    assert len(old) == 6
    assert old[0].content == "user msg 0"


# --- _call_summarizer message type handling ---


def test_call_summarizer_handles_all_message_types() -> None:
    from src.Agent.memory.summarise import _call_summarizer

    messages = [
        SystemMessage(content="system info"),
        HumanMessage(content="hello"),
        AIMessage(content="hi there"),
        ToolMessage(content='[{"name":"iphone","price":1000}]', tool_call_id="t1"),
    ]

    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "summary"
    mock_llm.invoke.return_value = mock_response

    with patch("src.Agent.memory.summarise._get_summarizer", return_value=mock_llm):
        result = _call_summarizer(messages)

    assert result == "summary"
    prompt = mock_llm.invoke.call_args[0][0][0].content
    assert "system: system info" in prompt
    assert "user: hello" in prompt
    assert "assistant: hi there" in prompt
    assert "tool:" in prompt


# --- memory_node ---


def test_memory_node_below_threshold() -> None:
    from src.Agent.nodes.memory import memory_node

    state = {"messages": _make_messages(9), "summary": None}
    result = memory_node(state)
    assert result == {}


def test_memory_node_above_threshold() -> None:
    from src.Agent.nodes.memory import memory_node

    state = {"messages": _make_messages(12), "summary": None}
    with patch("src.Agent.memory.summarise._call_summarizer", return_value="new summary"):
        result = memory_node(state)
    assert result["summary"] == "new summary"


def test_memory_node_appends_to_existing_summary() -> None:
    from src.Agent.nodes.memory import memory_node

    state = {"messages": _make_messages(12), "summary": "old summary"}
    with patch("src.Agent.memory.summarise._call_summarizer", return_value="new part"):
        result = memory_node(state)
    assert result["summary"] == "old summary\n\nnew part"
