import logging

from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool

from src.config.settings import settings

logger = logging.getLogger(__name__)

_pool: ConnectionPool | None = None
_checkpointer: PostgresSaver | None = None


def _get_pool() -> ConnectionPool:
    global _pool
    if _pool is None or _pool.closed:
        _pool = ConnectionPool(
            conninfo=settings.postgres.url,
            min_size=2,
            max_size=5,
            open=True,
            kwargs={"autocommit": True, "prepare_threshold": 0},
        )
        logger.info("Checkpoint connection pool created")
    return _pool


def get_checkpointer() -> PostgresSaver:
    global _checkpointer
    if _checkpointer is None:
        _checkpointer = PostgresSaver(_get_pool())
        _checkpointer.setup()
        logger.info("PostgresSaver ready (tables ensured)")
    return _checkpointer


def close_checkpointer() -> None:
    global _checkpointer
    if _pool is not None and not _pool.closed:
        _pool.close()
        logger.info("Checkpoint connection pool closed")
    _checkpointer = None
