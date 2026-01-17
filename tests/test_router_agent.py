"""Unit tests for Router Agent (Phase 9)."""

import uuid
from datetime import UTC, datetime
from uuid import UUID

import pytest

from src.agents import (
    AgentError,
    AgentResult,
    MockLLMClient,
    RouterAgent,
    StubSession,
    clear_registry,
    delegate_to_agent,
    get_agent,
    register_agent,
)
from src.agents.base import BaseAgent, SessionProtocol
from src.api.schemas import ConfirmationDetails, ErrorCode

# === Test AgentResult Model ===


def test_agent_result_model_basic() -> None:
    """Test AgentResult creation with text only."""
    result = AgentResult(text="Hello, world!")
    assert result.text == "Hello, world!"
    assert result.confirmation is None


def test_agent_result_model_with_confirmation() -> None:
    """Test AgentResult with confirmation details."""
    confirmation = ConfirmationDetails(
        code="BLUE-CACTUS-123",
        action_description="Delete pod nginx",
        expires_at=datetime.now(tz=UTC),
    )
    result = AgentResult(text="Confirm action", confirmation=confirmation)
    assert result.text == "Confirm action"
    assert result.confirmation is not None
    assert result.confirmation.code == "BLUE-CACTUS-123"


def test_agent_result_serialization() -> None:
    """Test AgentResult JSON serialization."""
    result = AgentResult(text="Test")
    data = result.model_dump()
    assert data["text"] == "Test"
    assert data["confirmation"] is None


# === Test MockLLMClient ===


@pytest.mark.asyncio
async def test_mock_llm_client_complete() -> None:
    """Test MockLLMClient returns mock response."""
    client = MockLLMClient()
    response = await client.complete("test prompt")
    assert response == "[MOCK] test prompt"


@pytest.mark.asyncio
async def test_mock_llm_client_with_system() -> None:
    """Test MockLLMClient ignores system prompt in mock mode."""
    client = MockLLMClient()
    response = await client.complete("query", system="You are a helpful assistant")
    assert response == "[MOCK] query"


# === Test StubSession ===


def test_stub_session_creation() -> None:
    """Test StubSession dataclass creation."""
    session_id = uuid.uuid4()
    session = StubSession(id=session_id, user_id=12345)
    assert session.id == session_id
    assert session.user_id == 12345


def test_stub_session_protocol_compliance() -> None:
    """Test StubSession satisfies SessionProtocol."""
    session = StubSession(id=uuid.uuid4(), user_id=999)
    # Protocol check: must have id and user_id attributes
    assert isinstance(session.id, UUID)
    assert isinstance(session.user_id, int)


# === Test RouterAgent ===


@pytest.mark.asyncio
async def test_router_agent_run_returns_echo() -> None:
    """Test RouterAgent returns echo response."""
    agent = RouterAgent()
    session = StubSession(id=uuid.uuid4(), user_id=123)

    result = await agent.run(session=session, query="Hello Teeshka", context={})

    assert isinstance(result, AgentResult)
    assert result.text == "Echo: Hello Teeshka"
    assert result.confirmation is None


@pytest.mark.asyncio
async def test_router_agent_name() -> None:
    """Test RouterAgent has correct name."""
    agent = RouterAgent()
    assert agent.name == "router"


@pytest.mark.asyncio
async def test_router_agent_with_context() -> None:
    """Test RouterAgent handles context (ignored in Phase 9)."""
    agent = RouterAgent()
    session = StubSession(id=uuid.uuid4(), user_id=456)

    result = await agent.run(
        session=session,
        query="What's the weather?",
        context={"source": "telegram", "urgency": "low"},
    )

    assert result.text == "Echo: What's the weather?"


# === Test Agent Registry ===


@pytest.fixture
def clean_registry():
    """Clear registry before and after test."""
    clear_registry()
    yield
    clear_registry()


def test_register_and_get_agent(clean_registry) -> None:
    """Test registering and retrieving agent."""
    _ = clean_registry  # Use fixture
    agent = RouterAgent()
    register_agent("ROUTER", agent)

    retrieved = get_agent("ROUTER")
    assert retrieved is agent


def test_get_agent_case_insensitive(clean_registry) -> None:
    """Test get_agent is case-insensitive."""
    _ = clean_registry  # Use fixture
    agent = RouterAgent()
    register_agent("sre", agent)

    assert get_agent("SRE") is agent
    assert get_agent("sre") is agent
    assert get_agent("Sre") is agent


def test_get_agent_not_found(clean_registry) -> None:
    """Test get_agent returns None for unknown category."""
    _ = clean_registry  # Use fixture
    assert get_agent("UNKNOWN") is None


@pytest.mark.asyncio
async def test_delegate_to_agent_success(clean_registry) -> None:
    """Test delegate_to_agent with registered agent."""
    _ = clean_registry  # Use fixture
    agent = RouterAgent()
    register_agent("ROUTER", agent)
    session = StubSession(id=uuid.uuid4(), user_id=789)

    response = await delegate_to_agent("ROUTER", session, "test query", {})

    assert response.text == "Echo: test query"
    assert response.agents_used == ["router", "router"]


@pytest.mark.asyncio
async def test_delegate_to_agent_not_found(clean_registry) -> None:
    """Test delegate_to_agent with unknown category."""
    _ = clean_registry  # Use fixture
    session = StubSession(id=uuid.uuid4(), user_id=999)

    response = await delegate_to_agent("UNKNOWN", session, "test", {})

    assert response.text == "Неизвестная категория запроса"
    assert response.agents_used == ["router"]


# === Test Agent Error Handling ===


class FailingAgent(BaseAgent):
    """Agent that always fails (for testing)."""

    name = "failing"

    async def run(
        self,
        session: SessionProtocol,  # noqa: ARG002
        query: str,  # noqa: ARG002
        context: dict,  # noqa: ARG002
    ) -> AgentResult:
        raise AgentError("Test failure")


@pytest.mark.asyncio
async def test_delegate_to_agent_handles_error(clean_registry) -> None:
    """Test delegate_to_agent catches AgentError."""
    _ = clean_registry  # Use fixture
    agent = FailingAgent()
    register_agent("FAILING", agent)
    session = StubSession(id=uuid.uuid4(), user_id=111)

    response = await delegate_to_agent("FAILING", session, "trigger error", {})

    assert response.text is None
    assert response.error is not None
    assert response.error.code == ErrorCode.INTERNAL_ERROR
    assert response.error.message == "Test failure"
    assert response.error.retryable is True
