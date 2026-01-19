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
import time
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
            # We cannot update the trace ID after creation, but we can add the
            # request trace_id as a tag for correlation.
            langfuse.update_current_trace(tags=[trace_id])
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


# Prompt caching
_prompt_cache: dict[str, tuple[float, object]] = {}
_cache_lock = asyncio.Lock()


async def get_prompt(name: str, cache_ttl: int = 300):
    """Fetch prompt from Langfuse with caching.

    Args:
        name: Prompt name in Langfuse (e.g., 'router.classification.v1')
        cache_ttl: Cache time-to-live in seconds (default 5 minutes)

    Returns:
        Prompt object or None if not found/disabled.
    """
    # Re-impl logic to get client safely locally to avoid circular deps if any
    settings = get_settings()
    if not settings.langfuse_public_key:
        return None

    try:
        # Use singleton if initialized
        client = init_langfuse()

        # Check cache with lock
        async with _cache_lock:
            if name in _prompt_cache:
                cached_time, cached_prompt = _prompt_cache[name]
                if time.time() - cached_time < cache_ttl:
                    return cached_prompt

        # Blocking call separate from lock to allow concurrency
        # Use asyncio.to_thread to avoid blocking event loop
        prompt = await asyncio.to_thread(client.get_prompt, name)

        # Update cache with lock
        async with _cache_lock:
            _prompt_cache[name] = (time.time(), prompt)

        return prompt
    except Exception:
        # Graceful failure - log debug to avoid spam
        # log.debug("langfuse_prompt_fetch_failed", prompt_name=name)
        return None


__all__ = [
    "get_langfuse",
    "get_prompt",
    "init_langfuse",
    "observe_request",
    "shutdown_langfuse",
]
