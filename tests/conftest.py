from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_langfuse_for_unit_tests(request):
    """Mock Langfuse client to prevent background threads in unit tests.

    This fixture automatically applies to all tests lacking the 'e2e' marker.
    It patches the Langfuse class where it is used in src.api.langfuse_client.
    """
    # Skip for E2E tests - they need real Langfuse
    if "e2e" in request.keywords:
        yield
        return

    # Mock Langfuse class to return a MagicMock
    # This prevents real background threads from starting
    with patch("src.api.langfuse_client.Langfuse") as MockLangfuse:
        mock_instance = MagicMock()
        MockLangfuse.return_value = mock_instance
        yield mock_instance
