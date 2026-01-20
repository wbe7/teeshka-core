"""E2E tests for Agents (Phase 11).

Verifies real LLM integration for Router and General agents.
Requires: LLM_API_KEY, LLM_MODEL_ROUTER, LLM_MODEL_GENERAL.
"""

import os
from unittest.mock import MagicMock

import pytest

from src.agents.general import GeneralAgent
from src.agents.router import RouterAgent
from src.api.settings import Settings
from src.llm.client import OpenRouterClient

# Constants
DEFAULT_ROUTER_MODEL = "nvidia/nemotron-3-nano-30b-a3b"
DEFAULT_GENERAL_MODEL = "google/gemini-3-flash-preview-20251217"


@pytest.fixture
def real_settings() -> Settings:
    """Create settings with real model names from env."""
    settings = MagicMock(spec=Settings)
    settings.llm_model_router = os.environ.get("LLM_MODEL_ROUTER", DEFAULT_ROUTER_MODEL)
    settings.llm_model_general = os.environ.get("LLM_MODEL_GENERAL", DEFAULT_GENERAL_MODEL)
    return settings


@pytest.fixture
def real_llm_client() -> OpenRouterClient:
    """Create real OpenRouter client."""
    api_key = os.environ.get("LLM_E2E_API_KEY") or os.environ.get("LLM_API_KEY")
    if not api_key:
        pytest.skip("LLM_API_KEY not set")

    return OpenRouterClient(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        model=os.environ.get("LLM_MODEL", "not-used-in-agent-e2e-tests"),
    )


@pytest.fixture
def general_agent(real_llm_client, real_settings) -> GeneralAgent:
    """Real General Agent."""
    return GeneralAgent(real_llm_client, real_settings)


@pytest.fixture
def router_agent(real_llm_client, real_settings, general_agent) -> RouterAgent:
    """Real Router Agent."""
    return RouterAgent(real_llm_client, real_settings, general_agent)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_router_classify_sre_real(router_agent) -> None:
    """Test real LLM classification for SRE query."""
    query = "Why is my nginx pod crashing?"
    result = await router_agent.run(None, query, {})

    # Expect routing to SRE
    assert "Routed to SRE" in result.text


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_router_delegation_general_real(router_agent) -> None:
    """Test real LLM routing -> General Agent -> Response."""
    query = "What is the capital of France?"
    result = await router_agent.run(None, query, {})

    # Should NOT be routed to SRE/Personal
    assert "Routed to" not in result.text
    # Should contain actual answer
    assert "Paris" in result.text


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_router_classify_personal_real(router_agent) -> None:
    """Test real LLM classification for Personal query."""
    query = "Remind me to call Mom at 5 PM."
    result = await router_agent.run(None, query, {})

    assert "Routed to PERSONAL" in result.text
