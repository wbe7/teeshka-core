"""Stub Session for Phase 9 (GEMINI.md §5)."""

from dataclasses import dataclass
from uuid import UUID


@dataclass
class StubSession:
    """Stub Session for Phase 9. Replaced with SQLAlchemy model in Phase 19."""

    id: UUID
    user_id: int
