"""Unit tests for General Agent."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.base import AgentResult
from src.agents.general import GeneralAgent
from src.api.settings import Settings


@pytest.fixture
def mock_llm_client():
    """Mock LLMClient."""
    client = AsyncMock()
    client.complete.return_value = "I am a helpful assistant."
    return client


@pytest.fixture
def mock_settings():
    """Mock Settings."""
    settings = MagicMock(spec=Settings)
    settings.llm_model_general = "google/gemini-3-flash-preview-20251217"
    return settings


@pytest.mark.asyncio
async def test_general_agent_initialization(mock_llm_client, mock_settings):
    """Test GeneralAgent initialization."""
    agent = GeneralAgent(mock_llm_client, mock_settings)
    assert agent.name == "general"
    assert agent.llm_client == mock_llm_client
    assert agent.settings == mock_settings


@pytest.mark.asyncio
async def test_general_agent_run(mock_llm_client, mock_settings):
    """Test GeneralAgent run method."""
    agent = GeneralAgent(mock_llm_client, mock_settings)
    query = "Hello!"

    result = await agent.run(None, query, {})

    assert isinstance(result, AgentResult)
    assert result.text == "I am a helpful assistant."

    # Verify LLM was called with correct model override
    mock_llm_client.complete.assert_called_once()
    call_args = mock_llm_client.complete.call_args
    assert call_args.kwargs["model"] == "google/gemini-3-flash-preview-20251217"
    assert call_args.kwargs["prompt"] == query
