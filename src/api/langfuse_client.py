"""Langfuse client and tracing utilities for Teeshka Core.

This module provides:
- Langfuse client initialization with Settings (§3.5)
- Tracing decorator with trace_id correlation
- FastAPI dependency injection for Langfuse client
- Graceful shutdown with flush()

Usage:
    from src.api.langfuse_client import get_langfuse, observe_request

    @observe_request
    async def my_handler(...):
        langfuse = get_langfuse()
        ...
"""

import asyncio
from collections.abc import Callable
from functools import lru_cache, wraps

from langfuse import Langfuse, get_client, observe

from src.api.logging import get_logger, get_trace_id
from src.api.settings import get_settings

log = get_logger(__name__)


@lru_cache
def init_langfuse() -> Langfuse:
    """Initialize Langfuse client with Settings (singleton).

    Uses constructor arguments from pydantic-settings.
    Environment variables are NOT used directly to avoid
    conflicts with Settings management (§2.5).

    Note: Langfuse SDK uses 'host=' parameter, not 'base_url='.
    """
    settings = get_settings()
    return Langfuse(
        public_key=settings.langfuse_public_key.get_secret_value(),
        secret_key=settings.langfuse_secret_key.get_secret_value(),
        host=settings.langfuse_base_url,
    )


def get_langfuse() -> Langfuse:
    """Get Langfuse client for FastAPI dependency injection.

    Example:
        @router.post("/query")
        async def query(langfuse: Langfuse = Depends(get_langfuse)):
            ...
    """
    return init_langfuse()


def shutdown_langfuse() -> None:
    """Flush pending events on shutdown.

    Call from FastAPI lifespan to ensure all traces are sent.
    """
    try:
        client = init_langfuse()
        client.flush()
    except Exception:
        log.exception("langfuse_flush_failed")


def observe_request[F: Callable](func: F) -> F:
    """Decorator to trace a function call with Langfuse.

    Wraps langfuse.observe() and adds custom trace metadata:
    - Correlates with existing trace_id from request context
    - Sets trace name from function name

    Supports both sync and async functions.

    Usage:
        @observe_request
        async def my_handler(request: TeeshkaRequest):
            ...
    """

    def _update_trace_from_context() -> None:
        """Get trace_id from context and update the Langfuse trace."""
        trace_id = get_trace_id()
        if not trace_id:
            return

        try:
            langfuse = get_client()
            langfuse.update_current_trace(id=trace_id)
        except Exception:
            log.warning("langfuse_trace_update_failed", trace_id=trace_id, exc_info=True)

    if asyncio.iscoroutinefunction(func):

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            _update_trace_from_context()
            return await func(*args, **kwargs)

        return observe()(async_wrapper)  # type: ignore[return-value]

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        _update_trace_from_context()
        return func(*args, **kwargs)

    return observe()(sync_wrapper)  # type: ignore[return-value]


__all__ = [
    "get_langfuse",
    "init_langfuse",
    "observe_request",
    "shutdown_langfuse",
]
