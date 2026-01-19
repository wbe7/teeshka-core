"""Unit tests for Router Agent."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.base import AgentResult
from src.agents.dependencies import LLMClient
from src.agents.general import GeneralAgent
from src.agents.router import RouterAgent
from src.api.settings import Settings


@pytest.fixture
def mock_llm_client():
    """Mock LLMClient."""
    client = AsyncMock(spec=LLMClient)
    client.complete.return_value = "SRE"  # Default response
    return client


@pytest.fixture
def mock_settings():
    """Mock Settings."""
    settings = MagicMock(spec=Settings)
    settings.llm_model_router = "nvidia/nemotron-3-nano-30b-a3b"
    return settings


@pytest.fixture
def mock_general_agent():
    """Mock GeneralAgent."""
    agent = AsyncMock(spec=GeneralAgent)
    agent.run.return_value = AgentResult(text="General Answer")
    agent.name = "general"
    return agent


@pytest.fixture
def router_agent(mock_llm_client, mock_settings, mock_general_agent):
    """Router Agent instance."""
    return RouterAgent(mock_llm_client, mock_settings, mock_general_agent)


@pytest.mark.asyncio
async def test_router_initialization(
    router_agent, mock_llm_client, mock_settings, mock_general_agent
):
    """Test RouterAgent initialization."""
    assert router_agent.name == "router"
    assert router_agent.llm_client == mock_llm_client
    assert router_agent.settings == mock_settings
    assert router_agent.general_agent == mock_general_agent


@pytest.mark.asyncio
async def test_router_classify_sre(router_agent, mock_llm_client):
    """Test classification and routing to SRE (Stub)."""
    mock_llm_client.complete.return_value = "SRE"
    query = "Why is pod crashing?"

    # Patch get_prompt to return None -> Force Default Prompt
    with patch("src.agents.router.get_prompt", new_callable=AsyncMock) as mock_get_prompt:
        mock_get_prompt.return_value = None

        result = await router_agent.run(None, query, {})

        assert isinstance(result, AgentResult)
        assert "Routed to SRE" in result.text

        # Verify classification call
        mock_llm_client.complete.assert_called_once()
        # Prompt should be the string from DEFAULT_ROUTER_PROMPT
        assert "Classify" in mock_llm_client.complete.call_args.kwargs["prompt"]


@pytest.mark.asyncio
async def test_router_delegation_to_general(router_agent, mock_llm_client, mock_general_agent):
    """Test routing to General Agent."""
    mock_llm_client.complete.return_value = "GENERAL"
    query = "Hi there"

    result = await router_agent.run(None, query, {})

    # Should return result from GeneralAgent
    assert result.text == "General Answer"

    # Verify delegation
    mock_general_agent.run.assert_called_once()


@pytest.mark.asyncio
async def test_router_unknown(router_agent, mock_llm_client):
    """Test UNKNOWN category handling."""
    mock_llm_client.complete.return_value = "UNKNOWN"
    query = "blabla"

    result = await router_agent.run(None, query, {})

    assert "I didn't understand" in result.text or "Clarify" in result.text


@pytest.mark.asyncio
async def test_router_error_handling(router_agent, mock_llm_client):
    """Test LLM error handling."""
    from src.llm.client import LLMError

    mock_llm_client.complete.side_effect = LLMError("LLM connection failed")
    query = "Any query"

    result = await router_agent.run(None, query, {})

    assert isinstance(result, AgentResult)
    assert "having trouble understanding you" in result.text
