"""LangSmith tracing setup + @traceable decorator for graph nodes.

LangSmith reads its configuration (LANGSMITH_* vars) from the process
environment.  This module loads those variables from the project's .env
file at import time so that running nodes from any entrypoint (tests,
scripts, uvicorn) is traced consistently.
"""
import logging
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except Exception:
    logging.getLogger(__name__).warning(
        "Could not load .env for LangSmith tracing", exc_info=True
    )

try:
    from langsmith import traceable as _langsmith_traceable
except ImportError:  # pragma: no cover - graceful degradation
    _langsmith_traceable = None


def traceable(
    name: str | None = None,
    run_type: str = "chain",
):
    """Decorator that wraps a graph-node function with LangSmith tracing.

    Falls back to a no-op passthrough when langsmith or an API key is
    unavailable, so tracing is optional and never breaks the graph.
    """
    if not (os.getenv("LANGSMITH_TRACING") == "true" and _langsmith_traceable):
        return lambda fn: fn
    return _langsmith_traceable(name=name, run_type=run_type)
