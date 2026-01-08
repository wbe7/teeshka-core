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

    pass


class AgentResult(BaseModel):
    """Standard result from any Teeshka agent."""

    text: str
    confirmation: ConfirmationDetails | None = None


class BaseAgent(ABC):
    """Abstract base for all Teeshka agents."""

    name: str

    @abstractmethod
    async def run(self, session: SessionProtocol, query: str, context: dict) -> AgentResult:
        """Execute agent logic and return result."""
        ...
