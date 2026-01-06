"""Pydantic response models for Teeshka Core API."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Response model for /health endpoint."""

    status: str


class ReadyCheck(BaseModel):
    """Health check results for external dependencies.

    Extended in future phases:
    - Phase 19: postgres
    - Phase 20: redis
    - Phase 21: mem0
    """

    postgres: bool | None = None
    redis: bool | None = None
    mem0: bool | None = None


class ReadyResponse(BaseModel):
    """Response model for /ready endpoint."""

    status: str
    checks: ReadyCheck
