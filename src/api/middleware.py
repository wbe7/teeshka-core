"""Request logging middleware for Teeshka Core.

This module provides:
- UUID7 trace_id generation (time-ordered) for request correlation
- X-Trace-ID header support for Langfuse correlation (Phase 7)
- Request lifecycle logging (started/completed/failed)
- Duration measurement in milliseconds

Note: Using uuid-utils for UUID7 on Python 3.12.
      Native uuid.uuid7() available in Python 3.14+.

Usage:
    app.add_middleware(RequestLoggingMiddleware)
"""

import time
from collections.abc import Awaitable, Callable

import uuid_utils
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.api.logging import bind_contextvars, clear_contextvars, get_logger

log = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for structured request logging with trace_id.

    Features:
        - Generates UUID7 trace_id for each request (time-ordered)
        - Accepts external X-Trace-ID header for distributed tracing
        - Logs request_started and request_completed events
        - Logs request_failed with exception info on errors
        - Measures request duration in milliseconds
        - Clears contextvars after each request to prevent leakage
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Process request with logging and trace_id binding.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware/handler in chain.

        Returns:
            HTTP response from downstream handler.
        """
        # Accept external trace_id or generate new UUID7 (time-ordered)
        trace_id = request.headers.get("X-Trace-ID") or str(uuid_utils.uuid7())

        # Clear any stale context and bind request context
        clear_contextvars()
        bind_contextvars(
            trace_id=trace_id,
            path=request.url.path,
            method=request.method,
        )

        log.info("request_started")
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            log.info(
                "request_completed",
                status_code=response.status_code,
                duration_ms=duration_ms,
            )
            return response
        except Exception:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            log.exception("request_failed", duration_ms=duration_ms)
            raise
        finally:
            clear_contextvars()
