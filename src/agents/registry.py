"""Agent registry for routing requests (GEMINI.md §5 Agent Registry)."""

from src.agents.base import AgentError, BaseAgent, SessionProtocol
from src.api.logging import get_trace_id
from src.api.schemas import ErrorCode, ErrorDetails, TeeshkaResponse

# Populated at startup, read-only during requests.
_agent_registry: dict[str, BaseAgent] = {}


def register_agent(category: str, agent: BaseAgent) -> None:
    """Register agent at app startup."""
    _agent_registry[category.upper()] = agent


def get_agent(category: str) -> BaseAgent | None:
    """Get agent by category."""
    return _agent_registry.get(category.upper())


def clear_registry() -> None:
    """Clear registry (for testing only)."""
    _agent_registry.clear()


async def delegate_to_agent(
    category: str, session: SessionProtocol, query: str, context: dict
) -> TeeshkaResponse:
    """Delegate request to specialized agent with error handling."""
    trace_id = get_trace_id() or "unknown"
    agent = _agent_registry.get(category.upper())
    if not agent:
        return TeeshkaResponse(
            text="Неизвестная категория запроса",
            agents_used=["router"],
            trace_id=trace_id,
        )

    try:
        result = await agent.run(session, query, context)
        return TeeshkaResponse(
            text=result.text,
            agents_used=["router", agent.name],
            trace_id=trace_id,
            confirmation_required=result.confirmation,
        )
    except AgentError as e:
        return TeeshkaResponse(
            text=None,
            error=ErrorDetails(code=ErrorCode.INTERNAL_ERROR, message=str(e), retryable=True),
            agents_used=["router", agent.name],
            trace_id=trace_id,
        )
