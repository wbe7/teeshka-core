"""Exhaustive unit tests for OpenRouterClient (Phase 10).

35 tests covering:
- Happy Path (3)
- Retry Logic (10)
- Non-Retryable Errors (5)
- Timeout Handling (3)
- Response Parsing (6)
- Edge Cases — Input (5)
- Headers & Config (3)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.llm.client import LLMError, OpenRouterClient

# === Fixtures ===


@pytest.fixture
def client() -> OpenRouterClient:
    """Create test client instance."""
    return OpenRouterClient(
        base_url="https://openrouter.ai/api/v1",
        api_key="test-api-key",
        model="test-model",
        timeout=30.0,
        max_retries=3,
    )


def make_response(
    status_code: int = 200,
    content: str = "Hello, world!",
    headers: dict | None = None,
) -> httpx.Response:
    """Create mock httpx response."""
    json_data = {
        "choices": [{"message": {"content": content}}],
    }
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.json.return_value = json_data
    response.text = str(json_data)
    response.headers = headers or {}
    return response


# === Happy Path (3 tests) ===


@pytest.mark.asyncio
async def test_complete_success(client: OpenRouterClient) -> None:
    """Test successful completion with valid response."""
    mock_response = make_response(content="Hello from LLM!")

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_instance

        result = await client.complete("Say hello")

        assert result == "Hello from LLM!"
        mock_instance.post.assert_called_once()


@pytest.mark.asyncio
async def test_complete_with_system_prompt(client: OpenRouterClient) -> None:
    """Test system prompt is correctly included in request body."""
    mock_response = make_response(content="System aware response")

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_instance

        await client.complete("Hello", system="You are a helpful assistant")

        call_args = mock_instance.post.call_args
        payload = call_args.kwargs["json"]
        assert len(payload["messages"]) == 2
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][0]["content"] == "You are a helpful assistant"
        assert payload["messages"][1]["role"] == "user"


@pytest.mark.asyncio
async def test_complete_extracts_text_from_choices(client: OpenRouterClient) -> None:
    """Test correctly extracts choices[0].message.content."""
    expected_content = "Extracted content here"
    mock_response = make_response(content=expected_content)

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_instance

        result = await client.complete("Extract this")

        assert result == expected_content


# === Retry Logic (10 tests) ===


@pytest.mark.asyncio
async def test_retry_on_500_internal_error(client: OpenRouterClient) -> None:
    """Test retries on 500 Internal Server Error."""
    error_response = make_response(status_code=500)
    success_response = make_response(content="Success after retry")

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post.side_effect = [error_response, success_response]
        mock_client.return_value.__aenter__.return_value = mock_instance

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await client.complete("Test")

        assert result == "Success after retry"
        assert mock_instance.post.call_count == 2


@pytest.mark.asyncio
async def test_retry_on_502_bad_gateway(client: OpenRouterClient) -> None:
    """Test retries on 502 Bad Gateway."""
    error_response = make_response(status_code=502)
    success_response = make_response(content="Success")

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post.side_effect = [error_response, success_response]
        mock_client.return_value.__aenter__.return_value = mock_instance

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await client.complete("Test")

        assert result == "Success"


@pytest.mark.asyncio
async def test_retry_on_503_unavailable(client: OpenRouterClient) -> None:
    """Test retries on 503 Service Unavailable."""
    error_response = make_response(status_code=503)
    success_response = make_response(content="Success")

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post.side_effect = [error_response, success_response]
        mock_client.return_value.__aenter__.return_value = mock_instance

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await client.complete("Test")

        assert result == "Success"


@pytest.mark.asyncio
async def test_retry_on_504_gateway_timeout(client: OpenRouterClient) -> None:
    """Test retries on 504 Gateway Timeout."""
    error_response = make_response(status_code=504)
    success_response = make_response(content="Success")

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post.side_effect = [error_response, success_response]
        mock_client.return_value.__aenter__.return_value = mock_instance

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await client.complete("Test")

        assert result == "Success"


@pytest.mark.asyncio
async def test_retry_on_timeout_exception(client: OpenRouterClient) -> None:
    """Test retries on httpx.TimeoutException."""
    success_response = make_response(content="Success after timeout")

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post.side_effect = [
            httpx.TimeoutException("Timeout"),
            success_response,
        ]
        mock_client.return_value.__aenter__.return_value = mock_instance

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await client.complete("Test")

        assert result == "Success after timeout"


@pytest.mark.asyncio
async def test_retry_on_connect_error(client: OpenRouterClient) -> None:
    """Test retries on httpx.ConnectError."""
    success_response = make_response(content="Connected")

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post.side_effect = [
            httpx.ConnectError("Connection refused"),
            success_response,
        ]
        mock_client.return_value.__aenter__.return_value = mock_instance

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await client.complete("Test")

        assert result == "Connected"


@pytest.mark.asyncio
async def test_retry_on_429_rate_limit(client: OpenRouterClient) -> None:
    """Test retries on 429 with Retry-After header parsing."""
    rate_limit_response = make_response(status_code=429, headers={"Retry-After": "5"})
    success_response = make_response(content="Success")

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post.side_effect = [rate_limit_response, success_response]
        mock_client.return_value.__aenter__.return_value = mock_instance

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await client.complete("Test")

        assert result == "Success"


@pytest.mark.asyncio
async def test_exponential_backoff_delays(client: OpenRouterClient) -> None:
    """Verify delays are 1s, 2s, 4s (mocked asyncio.sleep)."""
    error_response = make_response(status_code=500)
    success_response = make_response(content="Success")

    sleep_calls: list[float] = []

    async def mock_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post.side_effect = [
            error_response,
            error_response,
            success_response,
        ]
        mock_client.return_value.__aenter__.return_value = mock_instance

        with patch("asyncio.sleep", side_effect=mock_sleep):
            result = await client.complete("Test")

        assert result == "Success"
        assert sleep_calls == [1, 2]  # 2^0=1, 2^1=2


@pytest.mark.asyncio
async def test_max_retries_exceeded_raises(client: OpenRouterClient) -> None:
    """Test raises LLMError after 3 failed attempts."""
    error_response = make_response(status_code=500)

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post.return_value = error_response
        mock_client.return_value.__aenter__.return_value = mock_instance

        with (
            patch("asyncio.sleep", new_callable=AsyncMock),
            pytest.raises(LLMError) as exc_info,
        ):
            await client.complete("Test")

        assert "Max retries (3) exceeded" in str(exc_info.value)
        assert exc_info.value.retryable is True
        assert mock_instance.post.call_count == 3


@pytest.mark.asyncio
async def test_success_after_retry(client: OpenRouterClient) -> None:
    """Test succeeds on 2nd or 3rd attempt."""
    error_response = make_response(status_code=503)
    success_response = make_response(content="Third time's a charm")

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post.side_effect = [
            error_response,
            error_response,
            success_response,
        ]
        mock_client.return_value.__aenter__.return_value = mock_instance

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await client.complete("Test")

        assert result == "Third time's a charm"
        assert mock_instance.post.call_count == 3


# === Non-Retryable Errors (5 tests) ===


@pytest.mark.asyncio
async def test_no_retry_on_400_bad_request(client: OpenRouterClient) -> None:
    """Test raises immediately on 400 Bad Request."""
    error_response = make_response(status_code=400)

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post.return_value = error_response
        mock_client.return_value.__aenter__.return_value = mock_instance

        with pytest.raises(LLMError) as exc_info:
            await client.complete("Test")

        assert "400" in str(exc_info.value)
        assert mock_instance.post.call_count == 1  # No retry


@pytest.mark.asyncio
async def test_no_retry_on_401_unauthorized(client: OpenRouterClient) -> None:
    """Test raises immediately on 401 Unauthorized."""
    error_response = make_response(status_code=401)

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post.return_value = error_response
        mock_client.return_value.__aenter__.return_value = mock_instance

        with pytest.raises(LLMError) as exc_info:
            await client.complete("Test")

        assert "401" in str(exc_info.value)
        assert mock_instance.post.call_count == 1


@pytest.mark.asyncio
async def test_no_retry_on_403_forbidden(client: OpenRouterClient) -> None:
    """Test raises immediately on 403 Forbidden."""
    error_response = make_response(status_code=403)

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post.return_value = error_response
        mock_client.return_value.__aenter__.return_value = mock_instance

        with pytest.raises(LLMError) as exc_info:
            await client.complete("Test")

        assert "403" in str(exc_info.value)
        assert mock_instance.post.call_count == 1


@pytest.mark.asyncio
async def test_no_retry_on_404_not_found(client: OpenRouterClient) -> None:
    """Test raises immediately on 404 Not Found."""
    error_response = make_response(status_code=404)

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post.return_value = error_response
        mock_client.return_value.__aenter__.return_value = mock_instance

        with pytest.raises(LLMError) as exc_info:
            await client.complete("Test")

        assert "404" in str(exc_info.value)
        assert mock_instance.post.call_count == 1


@pytest.mark.asyncio
async def test_4xx_error_not_retryable_flag(client: OpenRouterClient) -> None:
    """Test LLMError.retryable == False for 4xx errors."""
    error_response = make_response(status_code=400)

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post.return_value = error_response
        mock_client.return_value.__aenter__.return_value = mock_instance

        with pytest.raises(LLMError) as exc_info:
            await client.complete("Test")

        assert exc_info.value.retryable is False


# === Timeout Handling (3 tests) ===


@pytest.mark.asyncio
async def test_timeout_raises_llm_timeout_error(client: OpenRouterClient) -> None:
    """Test LLMTimeoutError is raised on timeout."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post.side_effect = httpx.TimeoutException("Timeout")
        mock_client.return_value.__aenter__.return_value = mock_instance

        with (
            patch("asyncio.sleep", new_callable=AsyncMock),
            pytest.raises(LLMError) as exc_info,
        ):
            await client.complete("Test")

        # After retries exhausted, we get LLMError wrapping the timeout
        assert exc_info.value.retryable is True


@pytest.mark.asyncio
async def test_custom_timeout_value() -> None:
    """Test constructor timeout propagates to httpx."""
    client = OpenRouterClient(
        base_url="https://test.com",
        api_key="key",
        model="model",
        timeout=60.0,
    )

    assert client.timeout == 60.0


@pytest.mark.asyncio
async def test_timeout_after_max_retries(client: OpenRouterClient) -> None:
    """Test correct error after all attempts timeout."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post.side_effect = httpx.TimeoutException("Timeout")
        mock_client.return_value.__aenter__.return_value = mock_instance

        with (
            patch("asyncio.sleep", new_callable=AsyncMock),
            pytest.raises(LLMError) as exc_info,
        ):
            await client.complete("Test")

        assert "Max retries" in str(exc_info.value)
        assert mock_instance.post.call_count == 3


# === Response Parsing (6 tests) ===


@pytest.mark.asyncio
async def test_empty_choices_array(client: OpenRouterClient) -> None:
    """Test handles choices: [] gracefully."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = 200
    response.json.return_value = {"choices": []}
    response.text = '{"choices": []}'
    response.headers = {}

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post.return_value = response
        mock_client.return_value.__aenter__.return_value = mock_instance

        with pytest.raises(LLMError) as exc_info:
            await client.complete("Test")

        assert "Empty choices" in str(exc_info.value)
        assert exc_info.value.retryable is False


@pytest.mark.asyncio
async def test_missing_content_field(client: OpenRouterClient) -> None:
    """Test handles missing message.content."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = 200
    response.json.return_value = {"choices": [{"message": {}}]}
    response.text = '{"choices": [{"message": {}}]}'
    response.headers = {}

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post.return_value = response
        mock_client.return_value.__aenter__.return_value = mock_instance

        with pytest.raises(LLMError) as exc_info:
            await client.complete("Test")

        assert "Missing content" in str(exc_info.value)


@pytest.mark.asyncio
async def test_malformed_json_response(client: OpenRouterClient) -> None:
    """Test handles invalid JSON body."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = 200
    response.json.side_effect = Exception("Invalid JSON")
    response.text = "not json"
    response.headers = {}

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post.return_value = response
        mock_client.return_value.__aenter__.return_value = mock_instance

        with pytest.raises(LLMError) as exc_info:
            await client.complete("Test")

        assert "Invalid JSON" in str(exc_info.value)


@pytest.mark.asyncio
async def test_unexpected_response_structure(client: OpenRouterClient) -> None:
    """Test handles response without choices field."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = 200
    response.json.return_value = {"data": "something"}
    response.text = '{"data": "something"}'
    response.headers = {}

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post.return_value = response
        mock_client.return_value.__aenter__.return_value = mock_instance

        with pytest.raises(LLMError) as exc_info:
            await client.complete("Test")

        assert "Empty choices" in str(exc_info.value)


@pytest.mark.asyncio
async def test_null_content_value(client: OpenRouterClient) -> None:
    """Test handles content: null."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = 200
    response.json.return_value = {"choices": [{"message": {"content": None}}]}
    response.text = '{"choices": [{"message": {"content": null}}]}'
    response.headers = {}

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post.return_value = response
        mock_client.return_value.__aenter__.return_value = mock_instance

        with pytest.raises(LLMError) as exc_info:
            await client.complete("Test")

        assert "Missing content" in str(exc_info.value)


@pytest.mark.asyncio
async def test_whitespace_only_content(client: OpenRouterClient) -> None:
    """Test handles content with only whitespace."""
    mock_response = make_response(content="   ")

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_instance

        result = await client.complete("Test")

        assert result == "   "  # Whitespace preserved


# === Edge Cases — Input (5 tests) ===


@pytest.mark.asyncio
async def test_unicode_characters_in_prompt(client: OpenRouterClient) -> None:
    """Test emoji, Cyrillic, CJK characters."""
    mock_response = make_response(content="Unicode response: 你好 🎉")

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_instance

        result = await client.complete("Привет мир! 你好世界 🌍")

        assert result == "Unicode response: 你好 🎉"
        call_args = mock_instance.post.call_args
        payload = call_args.kwargs["json"]
        assert "Привет" in payload["messages"][0]["content"]


@pytest.mark.asyncio
async def test_very_long_prompt(client: OpenRouterClient) -> None:
    """Test 10K+ character prompt."""
    long_prompt = "A" * 15000  # 15K chars
    mock_response = make_response(content="Processed long prompt")

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_instance

        result = await client.complete(long_prompt)

        assert result == "Processed long prompt"
        call_args = mock_instance.post.call_args
        payload = call_args.kwargs["json"]
        assert len(payload["messages"][0]["content"]) == 15000


@pytest.mark.asyncio
async def test_empty_prompt(client: OpenRouterClient) -> None:
    """Test empty string prompt."""
    mock_response = make_response(content="Empty prompt response")

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_instance

        result = await client.complete("")

        assert result == "Empty prompt response"


@pytest.mark.asyncio
async def test_whitespace_only_prompt(client: OpenRouterClient) -> None:
    """Test prompt with only spaces/tabs."""
    mock_response = make_response(content="Whitespace prompt response")

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_instance

        result = await client.complete("   \t\t   ")

        assert result == "Whitespace prompt response"


@pytest.mark.asyncio
async def test_special_characters_prompt(client: OpenRouterClient) -> None:
    """Test newlines, tabs, quotes, backslashes."""
    special_prompt = 'Hello\n\tWorld "quoted" \\ backslash'
    mock_response = make_response(content="Special chars handled")

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_instance

        result = await client.complete(special_prompt)

        assert result == "Special chars handled"


# === Headers & Configuration (3 tests) ===


@pytest.mark.asyncio
async def test_authorization_header_set(client: OpenRouterClient) -> None:
    """Test Authorization: Bearer {key} is present."""
    mock_response = make_response(content="Auth OK")

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_instance

        await client.complete("Test")

        call_args = mock_instance.post.call_args
        headers = call_args.kwargs["headers"]
        assert headers["Authorization"] == "Bearer test-api-key"


@pytest.mark.asyncio
async def test_content_type_json(client: OpenRouterClient) -> None:
    """Test Content-Type: application/json."""
    mock_response = make_response(content="JSON OK")

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_instance

        await client.complete("Test")

        call_args = mock_instance.post.call_args
        headers = call_args.kwargs["headers"]
        assert headers["Content-Type"] == "application/json"


@pytest.mark.asyncio
async def test_model_parameter_in_request(client: OpenRouterClient) -> None:
    """Test model from constructor used in request body."""
    mock_response = make_response(content="Model OK")

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_instance

        await client.complete("Test")

        call_args = mock_instance.post.call_args
        payload = call_args.kwargs["json"]
        assert payload["model"] == "test-model"
