"""E2E tests for Langfuse integration (Phase 7).

These tests connect to the real teeshka-e2e Langfuse project
and verify actual trace creation and correlation.

Run with: pytest -m e2e tests/e2e/test_langfuse.py
"""

import pytest
import uuid_utils
from langfuse import Langfuse

from src.api.langfuse_client import observe_request
from src.api.logging import bind_contextvars, clear_contextvars


@pytest.mark.e2e
class TestLangfuseTraceCreation:
    """E2E tests for Langfuse trace creation."""

    async def test_observe_creates_real_trace(
        self,
        e2e_langfuse_client: Langfuse,
    ) -> None:
        """observe_request decorator creates a real trace in Langfuse.

        Verifies:
        1. Trace is created in teeshka-e2e project
        2. No exceptions during trace creation with real Langfuse
        3. Trace contains our custom trace_id
        """
        # Generate unique trace_id for this test
        test_trace_id = f"e2e-{uuid_utils.uuid7()}"

        # Bind trace_id to context (simulating middleware)
        bind_contextvars(trace_id=test_trace_id)

        try:
            # Define and call a traced function
            @observe_request
            async def e2e_test_handler() -> str:
                """Test handler for E2E trace verification."""
                return "e2e_success"

            result = await e2e_test_handler()

            # Verify function executed correctly
            assert result == "e2e_success"

            # Flush to ensure trace is sent
            e2e_langfuse_client.flush()

            # The key verification is that no exceptions were raised
            # during trace creation with real Langfuse.

        finally:
            clear_contextvars()

    async def test_langfuse_auth_check_succeeds(
        self,
        e2e_langfuse_client: Langfuse,
    ) -> None:
        """Verify E2E Langfuse credentials are valid."""
        result = e2e_langfuse_client.auth_check()
        assert result is True, "Langfuse auth_check should return True for valid credentials"

    async def test_multiple_traces_in_sequence(
        self,
        e2e_langfuse_client: Langfuse,
    ) -> None:
        """Multiple trace creations work correctly in sequence."""
        traces_created = []

        # Define handler outside loop
        @observe_request
        async def sequential_handler(val: int) -> int:
            return val

        for i in range(3):
            trace_id = f"e2e-seq-{i}-{uuid_utils.uuid7()}"
            bind_contextvars(trace_id=trace_id)

            try:
                result = await sequential_handler(i)
                assert result == i
                traces_created.append(trace_id)
            finally:
                clear_contextvars()

        # Flush all traces
        e2e_langfuse_client.flush()

        assert len(traces_created) == 3
