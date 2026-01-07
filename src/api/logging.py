"""Structured logging configuration for Teeshka Core.

This module provides:
- JSON formatted logs for K8s/Loki/ELK compatibility (§2.7)
- trace_id in every log for Langfuse correlation (§2.7)
- Exception logging with full stack traces (§3.6)

Usage:
    from src.api.logging import configure_logging, get_logger

    configure_logging("INFO")
    log = get_logger(__name__)
    log.info("message", key="value")
"""

import logging
import sys
from typing import TYPE_CHECKING

import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars, get_contextvars

if TYPE_CHECKING:
    from structlog.types import Processor


def configure_logging(level: str = "INFO") -> None:
    """Configure structlog with JSON output for K8s compatibility.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).

    Processors pipeline:
        1. merge_contextvars - Add trace_id, user_id from request context
        2. add_log_level - Add "level" field
        3. TimeStamper - Add ISO8601 UTC timestamp
        4. StackInfoRenderer - Include stack trace if requested
        5. format_exc_info - Format exceptions with traceback (§3.6)
        6. UnicodeDecoder - Handle bytes in log values
        7. JSONRenderer - Output as JSON for K8s (§2.7)
    """
    # Convert string level to logging constant
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Shared processors for both structlog and stdlib
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging handler with JSON output
    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    # Suppress noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a bound logger instance.

    Args:
        name: Logger name, typically __name__.

    Returns:
        Configured structlog BoundLogger.
    """
    return structlog.get_logger(name)


def get_trace_id() -> str | None:
    """Get current trace_id from contextvars.

    Returns:
        Current trace_id if bound, None otherwise.
        Used for Langfuse correlation (Phase 7).
    """
    ctx = get_contextvars()
    return ctx.get("trace_id")


__all__ = [
    "bind_contextvars",
    "clear_contextvars",
    "configure_logging",
    "get_logger",
    "get_trace_id",
]
