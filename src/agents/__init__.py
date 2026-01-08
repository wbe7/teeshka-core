"""Teeshka agents module (GEMINI.md §5)."""

from src.agents.base import AgentError, AgentResult, BaseAgent, SessionProtocol
from src.agents.dependencies import LLMClient, RouterDeps
from src.agents.llm_client import EchoLLMClient
from src.agents.registry import (
    clear_registry,
    delegate_to_agent,
    get_agent,
    register_agent,
)
from src.agents.router import RouterAgent
from src.agents.session import StubSession

__all__ = [
    "AgentError",
    "AgentResult",
    "BaseAgent",
    "EchoLLMClient",
    "LLMClient",
    "RouterAgent",
    "RouterDeps",
    "SessionProtocol",
    "StubSession",
    "clear_registry",
    "delegate_to_agent",
    "get_agent",
    "register_agent",
]
