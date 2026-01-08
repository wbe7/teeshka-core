"""Query endpoint - main entry point for Teeshka requests (GEMINI.md §9)."""

import uuid_utils
from fastapi import APIRouter, Depends

from src.agents import EchoLLMClient, RouterAgent, StubSession
from src.api.langfuse_client import observe_request
from src.api.logging import get_logger, get_trace_id
from src.api.schemas import TeeshkaRequest, TeeshkaResponse

router = APIRouter(tags=["query"])

log = get_logger(__name__)


def get_router_agent() -> RouterAgent:
    """DI factory for Router Agent."""
    return RouterAgent()


def get_llm_client() -> EchoLLMClient:
    """DI factory for LLM client. Replaced in Phase 10."""
    return EchoLLMClient()


@router.post("/query", response_model=TeeshkaResponse)
@observe_request
async def query(
    request: TeeshkaRequest,
    router_agent: RouterAgent = Depends(get_router_agent),  # noqa: B008
) -> TeeshkaResponse:
    """Process Teeshka query request.

    Uses Router Agent for processing. Phase 9: echo mode.
    Real routing to specialized agents in Phase 11+.
    """
    trace_id = get_trace_id()
    if trace_id is None:
        log.error("trace_id_missing", msg="trace_id not found in request context")
        trace_id = str(uuid_utils.uuid7())

    # Stub session until Phase 19 (SQLAlchemy models)
    session = StubSession(id=uuid_utils.uuid7(), user_id=request.user_id)

    result = await router_agent.run(
        session=session,
        query=request.query,
        context=request.context or {},
    )

    return TeeshkaResponse(
        text=result.text,
        agents_used=["router"],
        trace_id=trace_id,
    )
