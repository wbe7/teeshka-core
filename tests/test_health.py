"""Unit tests for health check endpoints."""

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

    def test_ready_checks_are_null_when_not_implemented(self) -> None:
        """Ready checks are null until dependencies are integrated."""
        response = client.get("/api/v1/ready")

        data = response.json()
        checks = data["checks"]
        assert checks["postgres"] is None
        assert checks["redis"] is None
        assert checks["mem0"] is None


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
