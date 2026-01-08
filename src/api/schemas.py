"""Pydantic models for Teeshka Core API (GEMINI.md §9, §3.6)."""

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, model_validator

# === Request Models (§9) ===


class Attachment(BaseModel):
    """Attachment for images, audio, files.

    Either `data` (base64 for small files <100KB) or `url` (for large files)
    must be provided, but not both.
    """

    type: Literal["image", "audio", "file"]
    mime_type: str
    data: str | None = None
    url: str | None = None

    @model_validator(mode="after")
    def validate_data_xor_url(self) -> "Attachment":
        """Ensure exactly one of data or url is provided."""
        if (self.data is None) == (self.url is None):
            raise ValueError("Exactly one of 'data' or 'url' must be provided")
        return self


class TeeshkaRequest(BaseModel):
    """Main request to Teeshka Core API."""

    query: str
    source: Literal["edge", "telegram", "web"]
    user_id: int  # BigInteger compatible (Telegram user ID)
    context: dict[str, Any] | None = None
    attachments: list[Attachment] = []


# === Error Models (§3.6) ===


class ErrorCode(str, Enum):
    """Error codes for clients."""

    K8S_CONNECTION_ERROR = "K8S_CONNECTION_ERROR"
    LLM_TIMEOUT = "LLM_TIMEOUT"
    MEM0_UNAVAILABLE = "MEM0_UNAVAILABLE"
    CONFIRMATION_EXPIRED = "CONFIRMATION_EXPIRED"
    CONFIRMATION_INVALID = "CONFIRMATION_INVALID"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ErrorDetails(BaseModel):
    """Error response structure."""

    code: ErrorCode
    message: str
    retryable: bool


# === Response Models (§9) ===


class ConfirmationDetails(BaseModel):
    """Destructive action confirmation request."""

    code: str  # e.g. "BLUE CACTUS", "RED DRAGON"
    action_description: str
    expires_at: datetime


class TeeshkaResponse(BaseModel):
    """Main response from Teeshka Core API."""

    version: str = "1.0"
    text: str | None = None
    agents_used: list[str] = []
    trace_id: str
    error: ErrorDetails | None = None
    confirmation_required: ConfirmationDetails | None = None


# === Health Models ===


class HealthResponse(BaseModel):
    """Response model for /health endpoint."""

    status: str


class ReadyCheck(BaseModel):
    """Health check results for external dependencies.

    Extended in future phases:
    - Phase 7: langfuse
    - Phase 8b: s3
    - Phase 19: postgres
    - Phase 20: redis
    - Phase 21: mem0
    """

    langfuse: bool | None = None
    s3: bool | None = None
    postgres: bool | None = None
    redis: bool | None = None
    mem0: bool | None = None


class ReadyResponse(BaseModel):
    """Response model for /ready endpoint."""

    status: str
    checks: ReadyCheck
