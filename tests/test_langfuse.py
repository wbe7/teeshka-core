"""Unit tests for Langfuse integration."""

import os
from unittest.mock import MagicMock, patch

import pytest

from src.api.langfuse_client import (
    get_langfuse,
    init_langfuse,
    observe_request,
    shutdown_langfuse,
)
from src.api.settings import get_settings

# Minimal valid environment for testing
VALID_ENV = {
    "ALLOWED_USER_ID": "123456789",
    "POSTGRES_URL": "postgresql+asyncpg://user:pass@localhost:5432/teeshka",
    "REDIS_URL": "redis://localhost:6379/0",
    "GEMINI_GATEWAY_URL": "http://localhost:8080",
    "TELEGRAM_BOT_TOKEN": "test_bot_token",
    "LLM_API_KEY": "test_llm_key",
    "GOOGLE_APPLICATION_CREDENTIALS_JSON": "base64_test_json",
    "LANGFUSE_PUBLIC_KEY": "pk-lf-test",
    "LANGFUSE_SECRET_KEY": "sk-lf-test",
    "S3_ACCESS_KEY": "test_access",
    "S3_SECRET_KEY": "test_secret",
}


@pytest.fixture(autouse=True)
def clear_caches():
    """Clear LRU caches before each test."""
    init_langfuse.cache_clear()
    get_settings.cache_clear()
    yield
    init_langfuse.cache_clear()
    get_settings.cache_clear()


class TestLangfuseInitialization:
    """Tests for Langfuse client initialization."""

    @patch("src.api.langfuse_client.Langfuse")
    def test_init_langfuse_uses_settings(self, mock_langfuse: MagicMock) -> None:
        """init_langfuse() passes credentials from Settings."""
        with patch.dict(os.environ, VALID_ENV, clear=True):
            init_langfuse()

        mock_langfuse.assert_called_once_with(
            public_key="pk-lf-test",
            secret_key="sk-lf-test",  # noqa: S106
            host="https://langfuse.cloudnative.space",
        )

    @patch("src.api.langfuse_client.Langfuse")
    def test_init_langfuse_singleton(self, mock_langfuse: MagicMock) -> None:
        """init_langfuse() returns cached singleton."""
        with patch.dict(os.environ, VALID_ENV, clear=True):
            client1 = init_langfuse()
            client2 = init_langfuse()

        assert client1 is client2
        mock_langfuse.assert_called_once()

    @patch("src.api.langfuse_client.Langfuse")
    def test_get_langfuse_returns_client(self, mock_langfuse: MagicMock) -> None:
        """get_langfuse() returns initialized client."""
        with patch.dict(os.environ, VALID_ENV, clear=True):
            client = get_langfuse()

        assert client is mock_langfuse.return_value


class TestLangfuseShutdown:
    """Tests for Langfuse shutdown."""

    @patch("src.api.langfuse_client.Langfuse")
    def test_shutdown_calls_flush(self, mock_langfuse: MagicMock) -> None:
        """shutdown_langfuse() calls flush() on client."""
        with patch.dict(os.environ, VALID_ENV, clear=True):
            init_langfuse()  # Initialize first
            shutdown_langfuse()

        mock_langfuse.return_value.flush.assert_called_once()

    @patch("src.api.langfuse_client.Langfuse")
    def test_shutdown_handles_exception(self, mock_langfuse: MagicMock) -> None:
        """shutdown_langfuse() handles exceptions gracefully."""
        mock_langfuse.return_value.flush.side_effect = Exception("Network error")

        with patch.dict(os.environ, VALID_ENV, clear=True):
            init_langfuse()
            # Should not raise
            shutdown_langfuse()


class TestObserveDecorator:
    """Tests for observe_request decorator."""

    @patch("src.api.langfuse_client.observe")
    @patch("src.api.langfuse_client.get_trace_id", return_value="test-trace-123")
    @patch("src.api.langfuse_client.get_client")
    async def test_observe_correlates_trace_id(
        self,
        mock_get_client: MagicMock,
        _mock_get_trace_id: MagicMock,
        mock_observe: MagicMock,
    ) -> None:
        """observe_request decorator sets trace_id from context."""
        # Setup mock observe to just call the function
        mock_observe.return_value = lambda f: f

        @observe_request
        async def my_handler():
            return "result"

        result = await my_handler()

        assert result == "result"
        mock_get_client.return_value.update_current_trace.assert_called_once_with(
            id="test-trace-123",
            name="my_handler",
        )

    @patch("src.api.langfuse_client.observe")
    @patch("src.api.langfuse_client.get_trace_id", return_value=None)
    @patch("src.api.langfuse_client.get_client")
    async def test_observe_skips_update_without_trace_id(
        self,
        mock_get_client: MagicMock,
        _mock_get_trace_id: MagicMock,
        mock_observe: MagicMock,
    ) -> None:
        """observe_request skips update_current_trace if no trace_id."""
        mock_observe.return_value = lambda f: f

        @observe_request
        async def my_handler():
            return "result"

        await my_handler()

        mock_get_client.return_value.update_current_trace.assert_not_called()

    @patch("src.api.langfuse_client.observe")
    @patch("src.api.langfuse_client.get_trace_id", return_value="test-trace")
    @patch("src.api.langfuse_client.get_client")
    async def test_observe_handles_update_exception(
        self,
        mock_get_client: MagicMock,
        _mock_get_trace_id: MagicMock,
        mock_observe: MagicMock,
    ) -> None:
        """observe_request handles update_current_trace exceptions gracefully."""
        mock_observe.return_value = lambda f: f
        mock_get_client.return_value.update_current_trace.side_effect = Exception("API error")

        @observe_request
        async def my_handler():
            return "result"

        # Should not raise, returns result anyway
        result = await my_handler()
        assert result == "result"

    @patch("src.api.langfuse_client.observe")
    @patch("src.api.langfuse_client.get_trace_id", return_value="test-trace")
    @patch("src.api.langfuse_client.get_client")
    def test_observe_sync_function(
        self,
        mock_get_client: MagicMock,
        _mock_get_trace_id: MagicMock,
        mock_observe: MagicMock,
    ) -> None:
        """observe_request works with sync functions."""
        mock_observe.return_value = lambda f: f

        @observe_request
        def my_sync_handler():
            return "sync_result"

        result = my_sync_handler()

        assert result == "sync_result"
        mock_get_client.return_value.update_current_trace.assert_called_once_with(
            id="test-trace",
            name="my_sync_handler",
        )

    @patch("src.api.langfuse_client.observe")
    def test_observe_preserves_function_metadata(
        self,
        mock_observe: MagicMock,
    ) -> None:
        """observe_request preserves function __name__ and __doc__."""
        mock_observe.return_value = lambda f: f

        @observe_request
        async def my_documented_handler():
            """This is the docstring."""
            return "result"

        assert my_documented_handler.__name__ == "my_documented_handler"
        assert my_documented_handler.__doc__ == "This is the docstring."
