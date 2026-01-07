"""Unit tests for request logging middleware."""

import logging
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.logging import clear_contextvars, configure_logging, get_trace_id
from src.api.middleware import RequestLoggingMiddleware


@pytest.fixture
def app() -> FastAPI:
    """Create test FastAPI app with middleware."""
    test_app = FastAPI()
    test_app.add_middleware(RequestLoggingMiddleware)

    @test_app.get("/test")
    def test_endpoint() -> dict:
        # Capture trace_id during request
        return {"trace_id": get_trace_id()}

    @test_app.get("/error")
    def error_endpoint() -> None:
        raise ValueError("Test error")

    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def setup_logging() -> None:
    """Configure logging before tests."""
    clear_contextvars()
    configure_logging("DEBUG")  # Use DEBUG to capture all logs
    yield
    clear_contextvars()


class TestTraceIdGeneration:
    """Tests for trace_id generation."""

    def test_generates_unique_trace_ids(self, client: TestClient) -> None:
        """Each request gets a unique trace_id."""
        response1 = client.get("/test")
        response2 = client.get("/test")

        trace_id_1 = response1.json()["trace_id"]
        trace_id_2 = response2.json()["trace_id"]

        assert trace_id_1 is not None
        assert trace_id_2 is not None
        assert trace_id_1 != trace_id_2

    def test_trace_id_is_valid_uuid(self, client: TestClient) -> None:
        """Generated trace_id is a valid UUID."""
        response = client.get("/test")
        trace_id = response.json()["trace_id"]

        # Should not raise
        uuid.UUID(trace_id)

    def test_accepts_external_trace_id_header(self, client: TestClient) -> None:
        """X-Trace-ID header is respected."""
        external_trace_id = "external-trace-12345"
        response = client.get(
            "/test",
            headers={"X-Trace-ID": external_trace_id},
        )

        assert response.json()["trace_id"] == external_trace_id


class TestRequestLifecycleLogging:
    """Tests for request lifecycle logging."""

    def test_logs_request_started_and_completed(
        self,
        client: TestClient,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Both request_started and request_completed events are logged."""
        with caplog.at_level(logging.INFO):
            client.get("/test")

        # structlog logs event in the message as dict-like string
        log_messages = " ".join(str(record.msg) for record in caplog.records)

        assert "request_started" in log_messages
        assert "request_completed" in log_messages

    def test_request_completed_has_duration_ms(
        self,
        client: TestClient,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """request_completed includes duration_ms."""
        with caplog.at_level(logging.INFO):
            client.get("/test")

        # Find request_completed log
        for record in caplog.records:
            msg = str(record.msg)
            if "request_completed" in msg:
                assert "duration_ms" in msg
                return

        pytest.fail("request_completed log not found")

    def test_request_completed_has_status_code(
        self,
        client: TestClient,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """request_completed includes status_code."""
        with caplog.at_level(logging.INFO):
            client.get("/test")

        for record in caplog.records:
            msg = str(record.msg)
            if "request_completed" in msg:
                assert "status_code" in msg
                assert "200" in msg
                return

        pytest.fail("request_completed log not found")

    def test_trace_id_in_log_output(
        self,
        client: TestClient,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Logs contain trace_id field."""
        with caplog.at_level(logging.INFO):
            response = client.get("/test")

        trace_id = response.json()["trace_id"]

        for record in caplog.records:
            msg = str(record.msg)
            if "request_started" in msg or "request_completed" in msg:
                assert trace_id in msg


class TestExceptionLogging:
    """Tests for exception logging."""

    def test_request_failed_logs_exception(
        self,
        client: TestClient,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Unhandled exceptions log request_failed with exception info."""
        with caplog.at_level(logging.INFO):
            client.get("/error")

        for record in caplog.records:
            msg = str(record.msg)
            if "request_failed" in msg:
                assert "duration_ms" in msg
                # Exception info should be attached
                return

        pytest.fail("request_failed log not found")


class TestContextCleanup:
    """Tests for context variable cleanup."""

    def test_contextvars_cleared_between_requests(self, client: TestClient) -> None:
        """Context variables are cleared between requests."""
        # First request with external trace_id
        response1 = client.get(
            "/test",
            headers={"X-Trace-ID": "first-trace"},
        )
        assert response1.json()["trace_id"] == "first-trace"

        # Second request without header should get new trace_id
        response2 = client.get("/test")
        trace_id_2 = response2.json()["trace_id"]

        assert trace_id_2 != "first-trace"
        # Should be a valid UUID (generated)
        uuid.UUID(trace_id_2)
