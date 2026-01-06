"""Health check endpoints for Teeshka Core."""

from fastapi import APIRouter

from src.api.schemas import HealthResponse, ReadyCheck, ReadyResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness probe for Kubernetes.

    Returns simple OK status. Used for K8s livenessProbe.
    """
    return HealthResponse(status="ok")


@router.get("/ready", response_model=ReadyResponse)
async def ready() -> ReadyResponse:
    """Readiness probe for Kubernetes.

    Returns OK status with dependency health checks.
    Extended in future phases:
    - Phase 19: PostgreSQL check
    - Phase 20: Redis check
    - Phase 21: Mem0 check
    """
    checks = ReadyCheck()
    return ReadyResponse(status="ok", checks=checks)
