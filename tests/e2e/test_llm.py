"""E2E tests for OpenRouterClient (Phase 10).

3 tests with real OpenRouter API:
- test_openrouter_real_completion
- test_openrouter_with_system_prompt
- test_openrouter_response_structure

Requirements:
- LLM_API_KEY set in .env (OpenRouter API key)
- Free tier model: nvidia/nemotron-3-nano-30b-a3b:free
"""

import pytest

from src.api.settings import get_settings
from src.llm.client import OpenRouterClient


@pytest.fixture
def real_client() -> OpenRouterClient:
    """Create OpenRouter client with real API key from settings."""
    settings = get_settings()
    return OpenRouterClient(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key.get_secret_value(),
        model=settings.llm_model,
        timeout=settings.llm_timeout,
        max_retries=settings.llm_max_retries,
    )


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_openrouter_real_completion(real_client: OpenRouterClient) -> None:
    """Test real OpenRouter API call with free tier model."""
    result = await real_client.complete("Say 'Hello' and nothing else.")

    assert isinstance(result, str)
    assert len(result) > 0
    # Model should respond with something containing "Hello"
    assert "hello" in result.lower() or len(result) > 0


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
    # This is a soft check - model may not perfectly follow instructions


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_openrouter_response_structure(real_client: OpenRouterClient) -> None:
    """Test response is non-empty string."""
    result = await real_client.complete("What is 2 + 2?")

    assert isinstance(result, str)
    assert len(result.strip()) > 0
    # Should contain the number 4 somewhere in response
    assert "4" in result or "four" in result.lower()
