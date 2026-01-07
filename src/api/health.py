"""Health check endpoints for Teeshka Core."""

from fastapi import APIRouter

from src.api.langfuse_client import get_langfuse
from src.api.logging import get_logger
from src.api.schemas import HealthResponse, ReadyCheck, ReadyResponse

router = APIRouter(tags=["health"])

log = get_logger(__name__)


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
    - Phase 7: Langfuse check
    - Phase 19: PostgreSQL check
    - Phase 20: Redis check
    - Phase 21: Mem0 check
    """
    langfuse_ok = _check_langfuse()
    checks = ReadyCheck(langfuse=langfuse_ok)
    return ReadyResponse(status="ok", checks=checks)


def _check_langfuse() -> bool:
    """Check Langfuse connectivity via auth_check()."""
    try:
        client = get_langfuse()
        return client.auth_check()
    except Exception:
        log.warning("langfuse_health_check_failed")
        return False
