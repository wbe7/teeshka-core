"""Configuration management for Teeshka Core using pydantic-settings.

This module provides centralized configuration management with:
- Environment variable loading
- .env file support for local development
- Type validation and conversion
- Secret handling with SecretStr

All settings are defined according to GEMINI.md section 2.5.
"""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Teeshka Core configuration loaded from environment variables.

    Required fields must be set via environment variables or .env file.
    Optional fields have sensible defaults.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # === Required (no defaults) ===
    allowed_user_id: int
    postgres_url: str
    redis_url: str
    gemini_gateway_url: str  # STT/TTS endpoint

    # === LLM Provider ===
    llm_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = "nvidia/nemotron-3-nano-30b-a3b:free"

    # === Secrets (required) ===
    telegram_bot_token: SecretStr
    llm_api_key: SecretStr
    google_application_credentials_json: SecretStr  # Base64 encoded JSON

    # === Secrets (optional) ===
    qdrant_api_key: SecretStr | None = None
    neo4j_password: SecretStr | None = None

    # === Langfuse (Observability) ===
    langfuse_public_key: SecretStr
    langfuse_secret_key: SecretStr
    langfuse_base_url: str = "https://langfuse.cloudnative.space"

    # === Langfuse E2E (teeshka-e2e project, optional) ===
    langfuse_e2e_public_key: SecretStr | None = None
    langfuse_e2e_secret_key: SecretStr | None = None

    # === Mem0 Self-hosted Server ===
    mem0_api_url: str = "http://mem0.teeshka.svc.cluster.local:8080"
    mem0_api_key: SecretStr | None = None

    # === MinIO/S3 (Attachments) ===
    s3_endpoint: str = "http://cloudnative.space:9000"
    s3_bucket: str = "teeshka-attachments"
    s3_access_key: SecretStr
    s3_secret_key: SecretStr

    # === Context Management ===
    model_context_limit: int = 32768
    summarization_trigger_ratio: float = 0.25

    # === Memory Management ===
    user_profile_max_facts: int = 5
    sliding_window_size: int = 20

    # === Summarization ===
    summarization_recent_messages: int = 5
    summarization_min_new_messages: int = 10

    # === Security ===
    confirmation_ttl_minutes: int = 5

    # === Logging ===
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL


@lru_cache
def get_settings() -> Settings:
    """Get cached Settings instance (singleton pattern).

    Uses lru_cache to ensure settings are loaded only once.
    This provides dependency injection compatibility with FastAPI.
    """
    return Settings()
