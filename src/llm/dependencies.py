"""Dependency injection for LLM client (GEMINI.md §2.6)."""

from functools import lru_cache

from src.api.settings import get_settings
from src.llm.client import OpenRouterClient


@lru_cache
def get_llm_client() -> OpenRouterClient:
    """Get cached OpenRouter client instance (singleton).

    Returns:
        OpenRouterClient configured from settings
    """
    settings = get_settings()
    return OpenRouterClient(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key.get_secret_value(),
        model=settings.llm_model,
        timeout=settings.llm_timeout,
        max_retries=settings.llm_max_retries,
    )
