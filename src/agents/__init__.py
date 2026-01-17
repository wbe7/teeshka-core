"""Teeshka agents module (GEMINI.md §5)."""

from src.agents.base import AgentError, AgentResult, BaseAgent, SessionProtocol
from src.agents.dependencies import LLMClient, RouterDeps
from src.agents.registry import (
    clear_registry,
    delegate_to_agent,
    get_agent,
    register_agent,
)
from src.agents.router import RouterAgent
from src.agents.session import StubSession


class MockLLMClient:
    """Mock LLM client for testing (CI-safe, no API calls).

    Replaces EchoLLMClient from Phase 9. Used in unit tests when
    we don't want to call the real OpenRouter API.
    """

    async def complete(self, prompt: str, system: str | None = None) -> str:  # noqa: ARG002
        """Return mock response (stub for testing)."""
        return f"[MOCK] {prompt}"


__all__ = [
    "AgentError",
    "AgentResult",
    "BaseAgent",
    "LLMClient",
    "MockLLMClient",
    "RouterAgent",
    "RouterDeps",
    "SessionProtocol",
    "StubSession",
    "clear_registry",
    "delegate_to_agent",
    "get_agent",
    "register_agent",
]
