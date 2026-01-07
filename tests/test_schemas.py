"""Unit tests for Pydantic API models (Phase 8)."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.api.schemas import (
    Attachment,
    ConfirmationDetails,
    ErrorCode,
    ErrorDetails,
    TeeshkaRequest,
    TeeshkaResponse,
)


class TestAttachment:
    """Tests for Attachment model with XOR validation."""

    def test_attachment_with_data(self) -> None:
        """Attachment with base64 data is valid."""
        attachment = Attachment(
            type="image",
            mime_type="image/png",
            data="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk",
        )
        assert attachment.data is not None
        assert attachment.url is None

    def test_attachment_with_url(self) -> None:
        """Attachment with URL is valid."""
        attachment = Attachment(
            type="audio",
            mime_type="audio/ogg",
            url="https://example.com/voice.ogg",
        )
        assert attachment.url is not None
        assert attachment.data is None

    def test_attachment_both_data_and_url_fails(self) -> None:
        """Attachment with both data and url raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Attachment(
                type="file",
                mime_type="application/pdf",
                data="base64content",
                url="https://example.com/file.pdf",
            )
        assert "Exactly one of" in str(exc_info.value)

    def test_attachment_neither_data_nor_url_fails(self) -> None:
        """Attachment without data or url raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Attachment(type="image", mime_type="image/jpeg")
        assert "Exactly one of" in str(exc_info.value)

    def test_attachment_invalid_type(self) -> None:
        """Invalid attachment type raises ValidationError."""
        with pytest.raises(ValidationError):
            Attachment(type="video", mime_type="video/mp4", url="https://example.com")


class TestTeeshkaRequest:
    """Tests for TeeshkaRequest model."""

    def test_teeshka_request_valid(self) -> None:
        """Valid request with all fields."""
        request = TeeshkaRequest(
            query="Check cluster status",
            source="telegram",
            user_id=123456789,
            context={"urgency": "high"},
            attachments=[
                Attachment(type="image", mime_type="image/png", url="https://x.com/img.png")
            ],
        )
        assert request.query == "Check cluster status"
        assert request.source == "telegram"
        assert request.user_id == 123456789
        assert request.context == {"urgency": "high"}
        assert len(request.attachments) == 1

    def test_teeshka_request_minimal(self) -> None:
        """Minimal valid request without optional fields."""
        request = TeeshkaRequest(
            query="Hello",
            source="edge",
            user_id=1,
        )
        assert request.context is None
        assert request.attachments == []

    def test_teeshka_request_invalid_source(self) -> None:
        """Invalid source raises ValidationError."""
        with pytest.raises(ValidationError):
            TeeshkaRequest(query="test", source="mobile", user_id=1)

    def test_teeshka_request_missing_query(self) -> None:
        """Missing query raises ValidationError."""
        with pytest.raises(ValidationError):
            TeeshkaRequest(source="web", user_id=1)  # type: ignore[call-arg]

    def test_teeshka_request_large_user_id(self) -> None:
        """Large user_id (Telegram BigInteger) is valid."""
        request = TeeshkaRequest(
            query="test",
            source="telegram",
            user_id=9223372036854775807,  # Max int64
        )
        assert request.user_id == 9223372036854775807


class TestErrorModels:
    """Tests for ErrorCode and ErrorDetails models."""

    def test_error_code_enum_values(self) -> None:
        """ErrorCode has all 7 expected values."""
        expected = {
            "K8S_CONNECTION_ERROR",
            "LLM_TIMEOUT",
            "MEM0_UNAVAILABLE",
            "CONFIRMATION_EXPIRED",
            "CONFIRMATION_INVALID",
            "VALIDATION_ERROR",
            "INTERNAL_ERROR",
        }
        actual = {e.value for e in ErrorCode}
        assert actual == expected

    def test_error_details_valid(self) -> None:
        """ErrorDetails model validates correctly."""
        error = ErrorDetails(
            code=ErrorCode.LLM_TIMEOUT,
            message="Request timed out after 30s",
            retryable=True,
        )
        assert error.code == ErrorCode.LLM_TIMEOUT
        assert error.retryable is True


class TestTeeshkaResponse:
    """Tests for TeeshkaResponse and ConfirmationDetails models."""

    def test_teeshka_response_serialization(self) -> None:
        """Response serializes correctly to JSON."""
        response = TeeshkaResponse(
            text="Hello!",
            agents_used=["router", "sre"],
            trace_id="abc-123",
        )
        data = response.model_dump()
        assert data["version"] == "1.0"
        assert data["text"] == "Hello!"
        assert data["agents_used"] == ["router", "sre"]
        assert data["error"] is None

    def test_teeshka_response_with_error(self) -> None:
        """Response with error serializes correctly."""
        response = TeeshkaResponse(
            text=None,
            agents_used=["router"],
            trace_id="xyz-789",
            error=ErrorDetails(
                code=ErrorCode.K8S_CONNECTION_ERROR,
                message="Cannot connect",
                retryable=True,
            ),
        )
        assert response.text is None
        assert response.error is not None
        assert response.error.code == ErrorCode.K8S_CONNECTION_ERROR

    def test_confirmation_details_datetime_iso8601(self) -> None:
        """ConfirmationDetails datetime serializes to ISO8601."""
        expires = datetime(2026, 1, 7, 20, 0, 0, tzinfo=UTC)
        confirmation = ConfirmationDetails(
            code="BLUE CACTUS",
            action_description="Delete pod nginx-abc",
            expires_at=expires,
        )
        data = confirmation.model_dump(mode="json")
        # ISO8601 format
        assert "2026-01-07" in data["expires_at"]
        assert confirmation.code == "BLUE CACTUS"

    def test_teeshka_response_with_confirmation(self) -> None:
        """Response with confirmation_required field."""
        response = TeeshkaResponse(
            text="Confirm deletion",
            agents_used=["router", "sre"],
            trace_id="conf-001",
            confirmation_required=ConfirmationDetails(
                code="RED DRAGON",
                action_description="Delete namespace prod",
                expires_at=datetime.now(UTC),
            ),
        )
        assert response.confirmation_required is not None
        assert response.confirmation_required.code == "RED DRAGON"
