"""Unit tests for health check endpoints."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


class TestHealthEndpoint:
    """Tests for /api/v1/health liveness probe."""

    def test_health_returns_ok(self) -> None:
        """Health endpoint returns status ok."""
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_health_response_content_type(self) -> None:
        """Health endpoint returns JSON content type."""
        response = client.get("/api/v1/health")

        assert response.headers["content-type"] == "application/json"


class TestReadyEndpoint:
    """Tests for /api/v1/ready readiness probe."""

    def test_ready_returns_ok_with_checks(self) -> None:
        """Ready endpoint returns status ok with checks dict."""
        response = client.get("/api/v1/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "checks" in data

    def test_ready_checks_langfuse_status(self) -> None:
        """Ready checks include Langfuse status."""
        response = client.get("/api/v1/ready")

        data = response.json()
        checks = data["checks"]
        # Langfuse check should return boolean (True if connected, False otherwise)
        assert checks["langfuse"] in (True, False)
        # Other checks still null
        assert checks["postgres"] is None
        assert checks["redis"] is None
        assert checks["mem0"] is None

    @patch("src.api.health._check_langfuse", return_value=True)
    def test_ready_langfuse_healthy(self, _mock_check) -> None:
        """Ready returns langfuse=True when connected."""
        response = client.get("/api/v1/ready")
        assert response.json()["checks"]["langfuse"] is True

    @patch("src.api.health._check_langfuse", return_value=False)
    def test_ready_langfuse_unhealthy(self, _mock_check) -> None:
        """Ready returns langfuse=False when disconnected."""
        response = client.get("/api/v1/ready")
        assert response.json()["checks"]["langfuse"] is False


class TestOpenAPIEndpoints:
    """Tests for OpenAPI documentation endpoints."""

    def test_openapi_json_available(self) -> None:
        """OpenAPI JSON schema is available at versioned URL."""
        response = client.get("/api/v1/openapi.json")

        assert response.status_code == 200
        data = response.json()
        assert data["info"]["title"] == "Teeshka Core"
        assert data["info"]["version"] == "0.1.0"

    def test_swagger_docs_available(self) -> None:
        """Swagger UI is available."""
        response = client.get("/api/v1/docs")

        assert response.status_code == 200
        assert "swagger" in response.text.lower()
