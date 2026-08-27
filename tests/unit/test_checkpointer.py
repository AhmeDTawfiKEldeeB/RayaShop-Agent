"""Unit tests for src.Agent.checkpointer — pool lifecycle and singleton behavior."""

from unittest.mock import MagicMock

import pytest
from langgraph.checkpoint.postgres import PostgresSaver


@pytest.fixture(autouse=True)
def _reset_globals():
    """Reset module-level singletons before every test."""
    import src.Agent.checkpointer as mod

    mod._pool = None
    mod._checkpointer = None
    yield
    if mod._pool is not None and not mod._pool.closed:
        mod._pool.close()
    mod._pool = None
    mod._checkpointer = None


def test_get_checkpointer_returns_postgres_saver():
    from src.Agent.checkpointer import get_checkpointer

    cp = get_checkpointer()
    assert isinstance(cp, PostgresSaver)


def test_get_checkpointer_is_singleton():
    from src.Agent.checkpointer import get_checkpointer

    a = get_checkpointer()
    b = get_checkpointer()
    assert a is b


def test_get_checkpointer_calls_setup_once():
    from src.Agent.checkpointer import get_checkpointer

    cp = get_checkpointer()
    # second call should NOT call setup again
    cp2 = get_checkpointer()
    assert cp is cp2


def test_pool_is_created_lazily():
    import src.Agent.checkpointer as mod

    assert mod._pool is None
    from src.Agent.checkpointer import get_checkpointer

    get_checkpointer()
    assert mod._pool is not None
    assert not mod._pool.closed


def test_close_checkpointer_closes_pool():
    from src.Agent.checkpointer import close_checkpointer, get_checkpointer

    get_checkpointer()
    import src.Agent.checkpointer as mod

    assert mod._pool is not None
    close_checkpointer()
    assert mod._checkpointer is None
    assert mod._pool.closed


def test_close_checkpointer_noop_when_not_initialized():
    from src.Agent.checkpointer import close_checkpointer

    close_checkpointer()  # should not raise


def test_reopen_after_close():
    from src.Agent.checkpointer import close_checkpointer, get_checkpointer

    cp1 = get_checkpointer()
    close_checkpointer()
    cp2 = get_checkpointer()
    assert cp1 is not cp2  # new instance
    assert isinstance(cp2, PostgresSaver)


def test_pool_uses_settings_url(monkeypatch):
    """Pool should be built from settings.postgres.url, not hardcoded."""
    monkeypatch.setattr(
        "src.Agent.checkpointer.settings.postgres",
        type("FakePostgres", (), {"url": "postgresql://u:p@remote:9999/mydb"})(),
    )

    captured_url = []
    fake_pool = MagicMock()

    def _fake_pool(conninfo="", **kw):
        captured_url.append(conninfo)
        return fake_pool

    monkeypatch.setattr("src.Agent.checkpointer.ConnectionPool", _fake_pool)
    monkeypatch.setattr(PostgresSaver, "setup", lambda self: None)

    from src.Agent.checkpointer import get_checkpointer

    cp = get_checkpointer()
    assert isinstance(cp, PostgresSaver)
    assert captured_url == ["postgresql://u:p@remote:9999/mydb"]


def test_get_returns_none_for_empty_thread():
    from src.Agent.checkpointer import get_checkpointer

    cp = get_checkpointer()
    result = cp.get({"configurable": {"thread_id": "nonexistent-thread"}})
    assert result is None
