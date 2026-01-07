"""Unit tests for Settings configuration management."""

import os
from unittest.mock import patch

import pytest
from pydantic import SecretStr, ValidationError

from src.api.settings import Settings, get_settings

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


class TestSettingsLoading:
    """Tests for loading Settings from environment variables."""

    def test_settings_loads_from_env(self) -> None:
        """Settings loads successfully with valid environment."""
        with patch.dict(os.environ, VALID_ENV, clear=True):
            settings = Settings()

            assert settings.allowed_user_id == 123456789
            assert settings.postgres_url == "postgresql+asyncpg://user:pass@localhost:5432/teeshka"
            assert settings.redis_url == "redis://localhost:6379/0"
            assert settings.gemini_gateway_url == "http://localhost:8080"

    def test_settings_validation_error_missing_required(self) -> None:
        """Settings raises ValidationError when required field is missing."""
        incomplete_env = {k: v for k, v in VALID_ENV.items() if k != "ALLOWED_USER_ID"}

        with patch.dict(os.environ, incomplete_env, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()

            errors = exc_info.value.errors()
            assert any(e["loc"] == ("allowed_user_id",) for e in errors)


class TestSettingsDefaults:
    """Tests for Settings default values."""

    def test_settings_default_values(self) -> None:
        """Settings uses correct default values when not overridden."""
        with patch.dict(os.environ, VALID_ENV, clear=True):
            settings = Settings()

            # LLM defaults
            assert settings.llm_base_url == "https://openrouter.ai/api/v1"
            assert settings.llm_model == "nvidia/nemotron-3-nano-30b-a3b:free"

            # Langfuse defaults
            assert settings.langfuse_base_url == "https://langfuse.cloudnative.space"

            # Mem0 defaults
            assert settings.mem0_api_url == "http://mem0.teeshka.svc.cluster.local:8080"
            assert settings.mem0_api_key is None

            # S3 defaults
            assert settings.s3_endpoint == "http://cloudnative.space:9000"
            assert settings.s3_bucket == "teeshka-attachments"

            # Context Management defaults
            assert settings.model_context_limit == 32768
            assert settings.summarization_trigger_ratio == 0.25

            # Memory Management defaults
            assert settings.user_profile_max_facts == 5
            assert settings.sliding_window_size == 20

            # Summarization defaults
            assert settings.summarization_recent_messages == 5
            assert settings.summarization_min_new_messages == 10

            # Security defaults
            assert settings.confirmation_ttl_minutes == 5

            # Optional secrets
            assert settings.qdrant_api_key is None
            assert settings.neo4j_password is None


class TestSecretStr:
    """Tests for SecretStr behavior."""

    def test_settings_secret_str_hidden(self) -> None:
        """SecretStr does not expose value in repr or str."""
        with patch.dict(os.environ, VALID_ENV, clear=True):
            settings = Settings()

            # SecretStr should not show actual value
            assert "test_bot_token" not in repr(settings.telegram_bot_token)
            assert "test_bot_token" not in str(settings.telegram_bot_token)
            assert "**********" in str(settings.telegram_bot_token)

    def test_settings_secret_str_get_value(self) -> None:
        """SecretStr provides value via get_secret_value()."""
        with patch.dict(os.environ, VALID_ENV, clear=True):
            settings = Settings()

            assert settings.telegram_bot_token.get_secret_value() == "test_bot_token"
            assert settings.llm_api_key.get_secret_value() == "test_llm_key"

    def test_settings_secret_types(self) -> None:
        """Required secrets are SecretStr types."""
        with patch.dict(os.environ, VALID_ENV, clear=True):
            settings = Settings()

            assert isinstance(settings.telegram_bot_token, SecretStr)
            assert isinstance(settings.llm_api_key, SecretStr)
            assert isinstance(settings.langfuse_public_key, SecretStr)
            assert isinstance(settings.langfuse_secret_key, SecretStr)
            assert isinstance(settings.s3_access_key, SecretStr)
            assert isinstance(settings.s3_secret_key, SecretStr)


class TestGetSettings:
    """Tests for get_settings() singleton function."""

    def test_get_settings_singleton(self) -> None:
        """get_settings() returns cached singleton instance."""
        # Clear cache before test
        get_settings.cache_clear()

        with patch.dict(os.environ, VALID_ENV, clear=True):
            settings1 = get_settings()
            settings2 = get_settings()

            assert settings1 is settings2

        # Clean up for other tests
        get_settings.cache_clear()
