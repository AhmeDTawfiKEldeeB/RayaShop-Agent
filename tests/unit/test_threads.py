"""Unit tests for src.Agent.memory.threads — list, history, delete helpers."""

from dataclasses import dataclass, field
from unittest.mock import MagicMock

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

# --------------------------------------------------------------------------- helpers

@dataclass
class _FakeConfig:
    configurable: dict = field(default_factory=dict)


@dataclass
class _FakeCheckpointTuple:
    config: dict
    checkpoint: dict
    metadata: dict | None = None


def _make_tpl(thread_id: str, *, meta: dict | None = None, msgs=None):
    ch = {}
    if msgs is not None:
        ch["channel_values"] = {"messages": msgs}
    return _FakeCheckpointTuple(
        config={"configurable": {"thread_id": thread_id}},
        checkpoint=ch,
        metadata=meta or {},
    )


def _human(text: str):
    return HumanMessage(content=text)


def _ai(text: str):
    return AIMessage(content=text)


# --------------------------------------------------------------------------- list_threads


class TestListThreads:
    def test_empty(self):
        from src.Agent.memory.threads import list_threads

        mock_cp = MagicMock()
        mock_cp.list.return_value = []
        assert list_threads(mock_cp) == []

    def test_single_thread(self):
        from src.Agent.memory.threads import list_threads

        tpl = _make_tpl("t1", meta={"created_at": "2026-01-01T00:00:00"})
        mock_cp = MagicMock()
        mock_cp.list.return_value = [tpl]
        result = list_threads(mock_cp)
        assert len(result) == 1
        assert result[0]["thread_id"] == "t1"
        assert result[0]["created_at"] == "2026-01-01T00:00:00"

    def test_deduplicates_same_thread(self):
        from src.Agent.memory.threads import list_threads

        tpls = [
            _make_tpl("t1", meta={"created_at": "2026-01-01T00:00:00"}),
            _make_tpl("t1", meta={"created_at": "2026-01-02T00:00:00"}),
        ]
        mock_cp = MagicMock()
        mock_cp.list.return_value = tpls
        result = list_threads(mock_cp)
        assert len(result) == 1
        # keeps the latest
        assert result[0]["created_at"] == "2026-01-02T00:00:00"

    def test_sorted_by_created_at_desc(self):
        from src.Agent.memory.threads import list_threads

        tpls = [
            _make_tpl("t1", meta={"created_at": "2026-01-01T00:00:00"}),
            _make_tpl("t2", meta={"created_at": "2026-03-01T00:00:00"}),
            _make_tpl("t3", meta={"created_at": "2026-02-01T00:00:00"}),
        ]
        mock_cp = MagicMock()
        mock_cp.list.return_value = tpls
        result = list_threads(mock_cp)
        ids = [t["thread_id"] for t in result]
        assert ids == ["t2", "t3", "t1"]

    def test_missing_metadata_gets_fallback(self):
        from src.Agent.memory.threads import list_threads

        tpl = _make_tpl("t1", meta=None)
        mock_cp = MagicMock()
        mock_cp.list.return_value = [tpl]
        result = list_threads(mock_cp)
        assert len(result) == 1
        # created_at should be a non-empty ISO string (fallback)
        assert "T" in result[0]["created_at"]


# --------------------------------------------------------------------------- get_thread_history


class TestGetThreadHistory:
    def test_empty(self):
        from src.Agent.memory.threads import get_thread_history

        mock_cp = MagicMock()
        mock_cp.list.return_value = []
        assert get_thread_history(mock_cp, "t1") == []

    def test_returns_user_and_ai_messages(self):
        from src.Agent.memory.threads import get_thread_history

        msgs = [_human("hi"), _ai("hello")]
        tpl = _make_tpl("t1", msgs=msgs)
        mock_cp = MagicMock()
        mock_cp.list.return_value = [tpl]
        result = get_thread_history(mock_cp, "t1")
        assert len(result) == 2
        assert result[0] == {"role": "user", "content": "hi"}
        assert result[1] == {"role": "assistant", "content": "hello"}

    def test_skips_system_messages(self):
        from src.Agent.memory.threads import get_thread_history

        msgs = [SystemMessage(content="sys"), _human("hi")]
        tpl = _make_tpl("t1", msgs=msgs)
        mock_cp = MagicMock()
        mock_cp.list.return_value = [tpl]
        result = get_thread_history(mock_cp, "t1")
        assert result == [{"role": "user", "content": "hi"}]

    def test_list_content_is_joined(self):
        from src.Agent.memory.threads import get_thread_history

        m = HumanMessage(content=[{"text": "part1"}, {"text": "part2"}])
        tpl = _make_tpl("t1", msgs=[m])
        mock_cp = MagicMock()
        mock_cp.list.return_value = [tpl]
        result = get_thread_history(mock_cp, "t1")
        assert result[0]["content"] == "part1 part2"


# --------------------------------------------------------------------------- delete_thread


class TestDeleteThread:
    def test_returns_false_when_no_checkpoints(self):
        from src.Agent.memory.threads import delete_thread

        mock_cp = MagicMock()
        mock_cp.list.return_value = []
        assert delete_thread(mock_cp, "t1") is False

    def test_deletes_and_returns_true(self):
        from src.Agent.memory.threads import delete_thread

        tpl = _make_tpl("t1")
        mock_cp = MagicMock()
        mock_cp.list.return_value = [tpl]
        assert delete_thread(mock_cp, "t1") is True
        mock_cp.delete_thread.assert_called_once_with("t1")
