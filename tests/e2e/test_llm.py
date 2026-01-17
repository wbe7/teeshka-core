"""E2E tests for OpenRouterClient (Phase 10).

3 tests with real OpenRouter API:
- test_openrouter_real_completion
- test_openrouter_with_system_prompt
- test_openrouter_response_structure

Requirements:
- LLM_API_KEY set in environment (OpenRouter API key)
- Free tier model: nvidia/nemotron-3-nano-30b-a3b:free
"""

import os

import pytest

from src.llm.client import OpenRouterClient

# Default values matching settings.py
DEFAULT_LLM_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_LLM_MODEL = "google/gemini-2.0-flash-exp:free"
DEFAULT_LLM_TIMEOUT = 30.0
DEFAULT_LLM_MAX_RETRIES = 7


@pytest.fixture
def real_client() -> OpenRouterClient:
    """Create OpenRouter client from environment variables.

    Uses LLM_API_KEY from env directly to avoid loading full Settings
    which requires all env vars (postgres, redis, etc.).
    """
    api_key = os.environ.get("LLM_API_KEY")
    if not api_key:
        pytest.skip("LLM_API_KEY not set in environment")

    return OpenRouterClient(
        base_url=os.environ.get("LLM_BASE_URL", DEFAULT_LLM_BASE_URL),
        api_key=api_key,
        model=os.environ.get("LLM_MODEL", DEFAULT_LLM_MODEL),
        timeout=float(os.environ.get("LLM_TIMEOUT", DEFAULT_LLM_TIMEOUT)),
        max_retries=int(os.environ.get("LLM_MAX_RETRIES", DEFAULT_LLM_MAX_RETRIES)),
    )


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_openrouter_real_completion(real_client: OpenRouterClient) -> None:
    """Test real OpenRouter API call with free tier model."""
    result = await real_client.complete("Say 'Hello' and nothing else.")

    assert isinstance(result, str)
    assert len(result) > 0
    # Model should respond with something containing "Hello"
    assert "hello" in result.lower()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_openrouter_with_system_prompt(real_client: OpenRouterClient) -> None:
    """Test system prompt affects response."""
    result = await real_client.complete(
        "What language am I speaking?",
        system="You are a helpful assistant. Always respond in Russian.",
    )

    assert isinstance(result, str)
    assert len(result) > 0
    # Response should contain some Russian characters or words
    # Check for Cyrillic unicode range (U+0400 to U+04FF)
    has_cyrillic = any("\u0400" <= char <= "\u04ff" for char in result)
    assert has_cyrillic, f"Response should contain Russian characters. Got: {result}"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_openrouter_response_structure(real_client: OpenRouterClient) -> None:
    """Test response is non-empty string."""
    result = await real_client.complete("What is 2 + 2?")

    assert isinstance(result, str)
    assert len(result.strip()) > 0
    # Should contain the number 4 somewhere in response
    assert "4" in result or "four" in result.lower()
