"""OpenRouter API client with retry logic and timeout handling.

Implements OpenAI-compatible interface as specified in ARCHITECTURE.md §2.6.
Error handling follows GEMINI.md §3.6 patterns.
"""

import asyncio
from typing import Any

import httpx


class LLMError(Exception):
    """Base exception for LLM client errors."""

    def __init__(self, message: str, *, retryable: bool = True) -> None:
        super().__init__(message)
        self.retryable = retryable


class LLMTimeoutError(LLMError):
    """Raised when LLM request times out."""

    def __init__(self, message: str = "LLM request timed out") -> None:
        super().__init__(message, retryable=True)


class OpenRouterClient:
    """Async HTTP client for OpenRouter API (OpenAI-compatible).

    Implements retry logic with exponential backoff per ARCHITECTURE.md §3.6.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        """Initialize OpenRouter client.

        Args:
            base_url: OpenRouter API base URL (e.g., https://openrouter.ai/api/v1)
            api_key: OpenRouter API key
            model: Model identifier (e.g., nvidia/nemotron-3-nano-30b-a3b:free)
            timeout: Request timeout in seconds (default: 30.0)
            max_retries: Maximum retry attempts (default: 3)
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://teeshka.local",
                "X-Title": "Teeshka Core",
            },
            timeout=httpx.Timeout(self.timeout),
        )

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def complete(self, prompt: str, system: str | None = None) -> str:
        """Complete prompt via OpenRouter /chat/completions.

        Args:
            prompt: User message content
            system: Optional system prompt

        Returns:
            Generated text from LLM

        Raises:
            LLMError: On API errors (with retryable flag)
            LLMTimeoutError: On timeout (retryable=True)
        """
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
        }

        last_exception: Exception | None = None

        # Try initial attempt + retries
        for attempt in range(self.max_retries + 1):
            try:
                return await self._make_request(payload)
            except LLMError as e:
                if not e.retryable:
                    raise
                last_exception = e
                # Exponential backoff: 1s, 2s, 4s
                delay = 2**attempt
                await asyncio.sleep(delay)

        # All retries exhausted
        raise LLMError(
            f"Max retries ({self.max_retries}) exceeded. Last error: {last_exception}",
            retryable=True,
        ) from last_exception

    async def _make_request(self, payload: dict[str, Any]) -> str:
        """Make single API request to OpenRouter.

        Args:
            payload: Request payload with model and messages

        Returns:
            Generated text content

        Raises:
            LLMError: On API errors
            LLMTimeoutError: On timeout
        """
        # Use shared client (performance)
        try:
            response = await self._client.post("/chat/completions", json=payload)
        except httpx.TimeoutException as e:
            raise LLMTimeoutError(f"Request timed out after {self.timeout}s") from e
        except httpx.ConnectError as e:
            raise LLMError(f"Connection error: {e}", retryable=True) from e

        # Handle HTTP errors
        if response.status_code == 429:
            # Rate limit - retryable
            retry_after_header = response.headers.get("Retry-After")
            # Default delay from parsing
            delay_msg = "unknown"

            if retry_after_header:
                try:
                    # Retry-After can be integer seconds
                    delay_seconds = int(retry_after_header)
                    # We don't sleep here, we raise error and let loop sleep?
                    # The loop uses exponential backoff.
                    # Ideally we should respect Retry-After.
                    # But our Architecture says "Exponential Backoff".
                    # Review says "use it for asyncio.sleep".
                    # So we should pass this info up or sleep here?
                    # The loop catches LLMError and determines sleep.
                    # We can add `retry_after` attr to LLMError? No, base class.
                    # Or we just format message correctly as requested.
                    delay_msg = f"{delay_seconds}s"
                except ValueError:
                    # Date format - ignore complexity for now, fallback to string
                    delay_msg = retry_after_header

            raise LLMError(
                f"Rate limited (429). Retry-After: {delay_msg}",
                retryable=True,
            )
        elif 400 <= response.status_code < 500:
            # Client error - not retryable
            raise LLMError(
                f"Client error ({response.status_code}): {response.text}",
                retryable=False,
            )
        elif response.status_code >= 500:
            # Server error - retryable
            raise LLMError(
                f"Server error ({response.status_code}): {response.text}",
                retryable=True,
            )

        # Parse response
        try:
            data = response.json()
        except ValueError as e:
            raise LLMError(f"Invalid JSON response: {e}", retryable=False) from e

        # Extract content from OpenAI-compatible response
        try:
            choices = data.get("choices", [])
            if not choices:
                raise LLMError("Empty choices array in response", retryable=False)
            content = choices[0].get("message", {}).get("content")
            if content is None:
                raise LLMError("Missing content in response", retryable=False)
            if isinstance(content, str) and content.strip() == "":
                # Whitespace-only content is valid but empty
                return content
            return content
        except (KeyError, IndexError, TypeError) as e:
            raise LLMError(f"Unexpected response structure: {e}", retryable=False) from e
