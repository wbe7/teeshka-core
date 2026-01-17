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

        for attempt in range(self.max_retries):
            try:
                return await self._make_request(payload)
            except LLMError as e:
                if not e.retryable:
                    raise
                last_exception = e
                # Exponential backoff: 1s, 2s, 4s
                delay = 2**attempt
                await asyncio.sleep(delay)
            except LLMTimeoutError:
                last_exception = LLMTimeoutError()
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
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://teeshka.local",
            "X-Title": "Teeshka Core",
        }

        async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout)) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
            except httpx.TimeoutException as e:
                raise LLMTimeoutError(f"Request timed out after {self.timeout}s") from e
            except httpx.ConnectError as e:
                raise LLMError(f"Connection error: {e}", retryable=True) from e

        # Handle HTTP errors
        if response.status_code == 429:
            # Rate limit - retryable
            retry_after = response.headers.get("Retry-After", "unknown")
            raise LLMError(
                f"Rate limited (429). Retry-After: {retry_after}",
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
        except Exception as e:
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
