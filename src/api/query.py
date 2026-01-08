"""Query endpoint - main entry point for Teeshka requests (GEMINI.md §9)."""

import uuid_utils
from fastapi import APIRouter

from src.api.langfuse_client import observe_request
from src.api.logging import get_logger, get_trace_id
from src.api.schemas import TeeshkaRequest, TeeshkaResponse

router = APIRouter(tags=["query"])

log = get_logger(__name__)


@router.post("/query", response_model=TeeshkaResponse)
@observe_request
async def query(request: TeeshkaRequest) -> TeeshkaResponse:
    """Process Teeshka query request.

    Stub implementation - returns echo response.
    Real routing to agents implemented in Phase 9+.
    """
    trace_id = get_trace_id()
    if trace_id is None:
        log.error("trace_id_missing", msg="trace_id not found in request context")
        trace_id = str(uuid_utils.uuid7())

    return TeeshkaResponse(
        text=f"Echo: {request.query}",
        agents_used=["router"],
        trace_id=trace_id,
    )
