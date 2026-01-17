# E2E Test Fixtures
"""E2E test configuration and fixtures.

E2E tests connect to real external services (Langfuse, S3/MinIO, OpenRouter, etc.)
and are marked with @pytest.mark.e2e.

Run E2E tests: pytest -m e2e
Run unit tests only: pytest -m "not e2e"

IMPORTANT: E2E fixtures use os.environ directly instead of get_settings()
to avoid requiring ALL environment variables (postgres, redis, etc.)
that are not needed for E2E tests.
"""

import os

import pytest
from langfuse import Langfuse

# Default values
DEFAULT_LANGFUSE_BASE_URL = "https://cloud.langfuse.com"
DEFAULT_S3_REGION = "us-east-1"


@pytest.fixture(scope="session")
def e2e_langfuse_client() -> Langfuse:
    """Langfuse client connected to teeshka-e2e project.

    Uses LANGFUSE_E2E_* environment variables directly.
    Scope: session (one client for all E2E tests).
    """
    public_key = os.environ.get("LANGFUSE_E2E_PUBLIC_KEY")
    secret_key = os.environ.get("LANGFUSE_E2E_SECRET_KEY")
    base_url = os.environ.get("LANGFUSE_BASE_URL", DEFAULT_LANGFUSE_BASE_URL)

    if not public_key or not secret_key:
        pytest.skip("LANGFUSE_E2E_PUBLIC_KEY and/or LANGFUSE_E2E_SECRET_KEY not set")

    # Set standard Langfuse env vars so @observe decorator works with E2E project
    os.environ["LANGFUSE_PUBLIC_KEY"] = public_key
    os.environ["LANGFUSE_SECRET_KEY"] = secret_key
    os.environ["LANGFUSE_HOST"] = base_url

    client = Langfuse(
        public_key=public_key,
        secret_key=secret_key,
        host=base_url,
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

    Uses S3_E2E_* env vars directly.
    Skips test if credentials not set.
    Scope: function (fresh client per test).
    """
    from src.storage.s3_client import S3Client

    endpoint = os.environ.get("S3_E2E_ENDPOINT")
    bucket = os.environ.get("S3_E2E_BUCKET", "teeshka-e2e")
    access_key = os.environ.get("S3_E2E_ACCESS_KEY")
    secret_key = os.environ.get("S3_E2E_SECRET_KEY")
    region = os.environ.get("S3_REGION", DEFAULT_S3_REGION)

    if not access_key or not secret_key:
        pytest.skip("S3_E2E_ACCESS_KEY and/or S3_E2E_SECRET_KEY not set")

    if not endpoint:
        pytest.skip("S3_E2E_ENDPOINT not set")

    client = S3Client(
        endpoint=endpoint,
        bucket=bucket,
        access_key=access_key,
        secret_key=secret_key,
        region=region,
        presigned_ttl=3600,  # Explicit TTL to avoid calling get_settings()
    )

    async with client:
        yield client
