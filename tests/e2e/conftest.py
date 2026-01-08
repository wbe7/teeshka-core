# E2E Test Fixtures
"""E2E test configuration and fixtures.

E2E tests connect to real external services (Langfuse, PostgreSQL, Redis, etc.)
and are marked with @pytest.mark.e2e.

Run E2E tests: pytest -m e2e
Run unit tests only: pytest -m "not e2e"
"""

import pytest
from langfuse import Langfuse

from src.api.settings import get_settings


@pytest.fixture(scope="session")
def e2e_langfuse_client() -> Langfuse:
    """Langfuse client connected to teeshka-e2e project.

    Uses LANGFUSE_E2E_* environment variables.
    Scope: session (one client for all E2E tests).
    """
    settings = get_settings()

    # Validate E2E credentials are set
    if not settings.langfuse_e2e_public_key or not settings.langfuse_e2e_secret_key:
        pytest.skip("LANGFUSE_E2E_PUBLIC_KEY and/or LANGFUSE_E2E_SECRET_KEY not set")

    client = Langfuse(
        public_key=settings.langfuse_e2e_public_key.get_secret_value(),
        secret_key=settings.langfuse_e2e_secret_key.get_secret_value(),
        host=settings.langfuse_base_url,
    )

    yield client

    # Flush any pending events
    client.flush()


@pytest.fixture
def e2e_trace_name(request: pytest.FixtureRequest) -> str:
    """Generate unique trace name from test function name."""
    return f"e2e_{request.node.name}"


@pytest.fixture(scope="function")
async def e2e_s3_client():
    """S3 client connected to real MinIO (teeshka-e2e bucket).

    Uses S3_E2E_* env vars (like Langfuse pattern).
    Skips test if credentials not set.
    Scope: function (fresh client per test).
    """
    from src.storage.s3_client import S3Client

    settings = get_settings()

    # Validate E2E credentials are set
    if not settings.s3_e2e_access_key or not settings.s3_e2e_secret_key:
        pytest.skip("S3_E2E_ACCESS_KEY and/or S3_E2E_SECRET_KEY not set")

    client = S3Client(
        endpoint=settings.s3_e2e_endpoint or settings.s3_endpoint,
        bucket=settings.s3_e2e_bucket,
        access_key=settings.s3_e2e_access_key.get_secret_value(),
        secret_key=settings.s3_e2e_secret_key.get_secret_value(),
        region=settings.s3_region,
    )

    async with client:
        yield client
