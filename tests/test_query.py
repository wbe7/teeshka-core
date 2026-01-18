"""Unit tests for /api/v1/query endpoint (Phase 8)."""


class TestQueryEndpoint:
    """Tests for POST /api/v1/query stub endpoint."""

    def test_query_returns_echo(self, client) -> None:
        """Stub returns echo of query."""
        response = client.post(
            "/api/v1/query",
            json={
                "query": "Hello, Teeshka!",
                "source": "telegram",
                "user_id": 123456,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "Echo: Hello, Teeshka!"

    def test_query_returns_trace_id(self, client) -> None:
        """Response includes trace_id."""
        response = client.post(
            "/api/v1/query",
            json={"query": "test", "source": "edge", "user_id": 1},
        )
        assert response.status_code == 200
        data = response.json()
        assert "trace_id" in data
        # Validate that trace_id is a valid UUID
        from uuid import UUID

        UUID(data["trace_id"])  # Raises ValueError if invalid

    def test_query_agents_used(self, client) -> None:
        """Response includes agents_used with router."""
        response = client.post(
            "/api/v1/query",
            json={"query": "test", "source": "web", "user_id": 42},
        )
        assert response.status_code == 200
        data = response.json()
        assert "router" in data["agents_used"]

    def test_query_validation_error(self, client) -> None:
        """422 on invalid request body."""
        response = client.post(
            "/api/v1/query",
            json={"query": "test"},  # Missing source and user_id
        )
        assert response.status_code == 422  # Unprocessable Entity

    def test_query_invalid_source(self, client) -> None:
        """422 on invalid source value."""
        response = client.post(
            "/api/v1/query",
            json={"query": "test", "source": "invalid", "user_id": 1},
        )
        assert response.status_code == 422

    def test_query_in_openapi(self, client) -> None:
        """POST /query appears in OpenAPI spec."""
        response = client.get("/api/v1/openapi.json")
        assert response.status_code == 200
        spec = response.json()
        assert "/api/v1/query" in spec["paths"]
        assert "post" in spec["paths"]["/api/v1/query"]

    def test_query_response_version(self, client) -> None:
        """Response includes version 1.0."""
        response = client.post(
            "/api/v1/query",
            json={"query": "check", "source": "telegram", "user_id": 999},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "1.0"
