"""Base classes for Teeshka agents (GEMINI.md §5 Agent Interface)."""

from abc import ABC, abstractmethod
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel

from src.api.schemas import ConfirmationDetails


class SessionProtocol(Protocol):
    """Protocol for Session - replaced with SQLAlchemy model in Phase 19."""

    id: UUID
    user_id: int


class AgentError(Exception):
    """Base exception for agent failures."""

    def __init__(self, message: str, *, retryable: bool = True) -> None:
        super().__init__(message)
        self.retryable = retryable


class AgentResult(BaseModel):
    """Standard result from any Teeshka agent."""

    text: str | None = None
    confirmation: ConfirmationDetails | None = None
    needs_enrichment: str | None = None  # e.g. "MEMORY", "CURRENT_TIME"


class BaseAgent(ABC):
    """Abstract base for all Teeshka agents."""

    name: str

    @abstractmethod
    async def run(self, session: SessionProtocol, query: str, context: dict) -> AgentResult:
        """Execute agent logic and return result."""
        ...
