from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from dotenv import load_dotenv

load_dotenv()


@pytest.fixture(autouse=True)
def mock_langfuse_for_unit_tests(request):
    """Mock Langfuse client to prevent background threads in unit tests.

    This fixture automatically applies to all tests lacking the 'e2e' marker.
    It patches the Langfuse class where it is used in src.api.langfuse_client.
    """
    # Skip for E2E tests - they need real Langfuse
    if "e2e" in request.keywords:
        yield
        return

    # Mock Langfuse class to return a MagicMock
    # This prevents real background threads from starting
    with patch("src.api.langfuse_client.Langfuse") as MockLangfuse:
        mock_instance = MagicMock()
        MockLangfuse.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_llm_client_fixture():
    """Mock LLMClient for API tests."""
    mock = AsyncMock()
    # Default behavior: return "GENERAL" to trigger GeneralAgent,
    # which calls it again and gets "GENERAL" as text.
    # We can refine this using side_effect in specific tests if needed.
    mock.complete.return_value = "GENERAL"
    return mock


@pytest.fixture
def mock_router_agent_fixture():
    """Mock Router Agent for API tests."""
    from src.agents import AgentResult

    mock = AsyncMock()
    # Explicitly set run methods
    mock.run = AsyncMock()
    mock.run.return_value = AgentResult(
        text="GENERAL",
        confirmation=None,
    )
    return mock


@pytest.fixture
def client(mock_llm_client_fixture, mock_router_agent_fixture):
    """Test client with application lifespan support and mocked dependencies."""
    from fastapi.testclient import TestClient

    from src.api.main import app
    from src.api.query import get_router_agent
    from src.llm.dependencies import get_llm_client

    # Override LLM client (for other endpoints if any)
    app.dependency_overrides[get_llm_client] = lambda: mock_llm_client_fixture
    # Override Router Agent (for query endpoint)
    app.dependency_overrides[get_router_agent] = lambda: mock_router_agent_fixture

    # Patch OpenRouterClient and Agents in main to prevent lifespan failure
    with (
        patch("src.api.main.OpenRouterClient") as MockLLMClient,
        patch("src.api.main.GeneralAgent"),
        patch("src.api.main.RouterAgent"),
    ):
        # Ensure llm_client.aclose is awaitable
        mock_llm_instance = MockLLMClient.return_value
        mock_llm_instance.aclose = AsyncMock()

        with TestClient(app) as c:
            yield c

    app.dependency_overrides.clear()
