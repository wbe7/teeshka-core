"""Unit tests for structured logging module."""

import json
import logging
from io import StringIO
from unittest.mock import patch

import pytest
import structlog

from src.api.logging import (
    bind_contextvars,
    clear_contextvars,
    configure_logging,
    get_logger,
    get_trace_id,
)


@pytest.fixture(autouse=True)
def reset_logging() -> None:
    """Reset logging configuration before each test."""
    clear_contextvars()
    # Reset structlog
    structlog.reset_defaults()
    # Clear root logger handlers
    root = logging.getLogger()
    root.handlers.clear()
    yield
    clear_contextvars()


class TestConfigureLogging:
    """Tests for configure_logging function."""

    def test_json_output_format(self) -> None:
        """Log output is valid JSON."""
        output = StringIO()
        with patch("sys.stdout", output):
            configure_logging("INFO")
            log = get_logger("test")
            log.info("test_event", key="value")

        # Get the last line (actual log)
        lines = output.getvalue().strip().split("\n")
        assert len(lines) >= 1

        # Parse JSON
        log_entry = json.loads(lines[-1])
        assert log_entry["event"] == "test_event"
        assert log_entry["key"] == "value"

    def test_log_contains_timestamp_iso(self) -> None:
        """Log contains ISO8601 UTC timestamp."""
        output = StringIO()
        with patch("sys.stdout", output):
            configure_logging("INFO")
            log = get_logger("test")
            log.info("test_event")

        lines = output.getvalue().strip().split("\n")
        log_entry = json.loads(lines[-1])

        assert "timestamp" in log_entry
        # ISO8601 format ends with Z for UTC
        assert log_entry["timestamp"].endswith("Z") or "+" in log_entry["timestamp"]

    def test_log_contains_level(self) -> None:
        """Log contains level field."""
        output = StringIO()
        with patch("sys.stdout", output):
            configure_logging("INFO")
            log = get_logger("test")
            log.warning("test_warning")

        lines = output.getvalue().strip().split("\n")
        log_entry = json.loads(lines[-1])

        assert "level" in log_entry
        assert log_entry["level"] == "warning"

    def test_exception_includes_stack_trace(self) -> None:
        """log.exception() includes exception info with stack trace."""
        output = StringIO()
        with patch("sys.stdout", output):
            configure_logging("INFO")
            log = get_logger("test")

            try:
                raise ValueError("Test error")
            except ValueError:
                log.exception("error_occurred")

        lines = output.getvalue().strip().split("\n")
        log_entry = json.loads(lines[-1])

        assert log_entry["event"] == "error_occurred"
        assert "exception" in log_entry
        assert "ValueError" in log_entry["exception"]
        assert "Test error" in log_entry["exception"]

    def test_log_level_from_settings(self) -> None:
        """Log level respects configured level."""
        output = StringIO()
        with patch("sys.stdout", output):
            configure_logging("WARNING")
            log = get_logger("test")
            log.info("should_not_appear")
            log.warning("should_appear")

        lines = output.getvalue().strip().split("\n")
        # Filter out empty lines
        lines = [line for line in lines if line.strip()]

        # Only warning should appear
        assert len(lines) == 1
        log_entry = json.loads(lines[0])
        assert log_entry["event"] == "should_appear"


class TestGetLogger:
    """Tests for get_logger function."""

    def test_returns_bound_logger(self) -> None:
        """get_logger returns a BoundLogger instance."""
        configure_logging("INFO")
        log = get_logger("test.module")

        assert hasattr(log, "info")
        assert hasattr(log, "warning")
        assert hasattr(log, "error")
        assert hasattr(log, "exception")


class TestGetTraceId:
    """Tests for get_trace_id function."""

    def test_returns_none_when_not_bound(self) -> None:
        """get_trace_id returns None when no trace_id is bound."""
        clear_contextvars()
        assert get_trace_id() is None

    def test_returns_bound_value(self) -> None:
        """get_trace_id returns the bound trace_id."""
        clear_contextvars()
        bind_contextvars(trace_id="test-trace-123")

        assert get_trace_id() == "test-trace-123"
