"""Stub LLM client for Phase 9 (real implementation in Phase 10)."""


class EchoLLMClient:
    """Stub LLM client that echoes input. Replaced in Phase 10."""

    async def complete(self, prompt: str, system: str | None = None) -> str:  # noqa: ARG002
        """Return echo response (stub for testing)."""
        return f"[ECHO] {prompt}"
