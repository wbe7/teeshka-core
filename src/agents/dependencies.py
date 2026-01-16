"""Dependency injection types for agents (GEMINI.md §2.6)."""

from dataclasses import dataclass
from typing import Protocol


class LLMClient(Protocol):
    """Protocol for LLM clients (implemented in Phase 10)."""

    async def complete(self, prompt: str, system: str | None = None) -> str:
        """Complete prompt with LLM."""
        ...


@dataclass
class RouterDeps:
    """Dependencies injected into Router Agent."""

    llm_client: LLMClient
    trace_id: str
    user_id: int
