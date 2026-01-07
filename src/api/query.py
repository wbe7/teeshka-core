"""Query endpoint - main entry point for Teeshka requests (GEMINI.md §9)."""

from fastapi import APIRouter

from src.api.langfuse_client import observe_request
from src.api.logging import get_trace_id
from src.api.schemas import TeeshkaRequest, TeeshkaResponse

router = APIRouter(tags=["query"])


@router.post("/query", response_model=TeeshkaResponse)
@observe_request
async def query(request: TeeshkaRequest) -> TeeshkaResponse:
    """Process Teeshka query request.

    Stub implementation - returns echo response.
    Real routing to agents implemented in Phase 9+.
    """
    return TeeshkaResponse(
        text=f"Echo: {request.query}",
        agents_used=["router"],
        trace_id=get_trace_id() or "unknown",
    )
