import logging
from typing import Any
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool

from src.config.settings import settings

logger = logging.getLogger(__name__)

_pool = None
_checkpointer = None

def get_checkpointer() -> Any:
    """Lazily initialize the PostgreSQL connection pool and checkpointer.
    Falls back to MemorySaver if PostgreSQL is unreachable (e.g. during local dev without docker).
    """
    global _pool, _checkpointer
    if _checkpointer is None:
        try:
            conn_info = f"postgresql://{settings.postgres.user}:{settings.postgres.password}@{settings.postgres.host}:{settings.postgres.port}/{settings.postgres.database}"
            _pool = ConnectionPool(conninfo=conn_info, max_size=5, open=True, timeout=2.0)
            _checkpointer = PostgresSaver(_pool)
            _checkpointer.setup()
            logger.info("PostgreSQL checkpointer connected successfully.")
        except Exception as exc:
            logger.warning("Could not connect to PostgreSQL checkpointer (%s). Falling back to in-memory MemorySaver.", exc)
            if _pool is not None:
                try:
                    _pool.close()
                except Exception:
                    pass
                _pool = None
            _checkpointer = MemorySaver()
    return _checkpointer

def close_checkpointer():
    global _pool, _checkpointer
    if _pool is not None:
        try:
            _pool.close()
        except Exception:
            pass
        _pool = None
    _checkpointer = None

