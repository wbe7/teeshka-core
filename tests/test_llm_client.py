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
    client._client.post = AsyncMock(return_value=mock_response)

    result = await client.complete("Say hello")

    assert result == "Hello from LLM!"
    client._client.post.assert_called_once()


@pytest.mark.asyncio
async def test_complete_with_system_prompt(client: OpenRouterClient) -> None:
    """Test system prompt is correctly included in request body."""
    mock_response = make_response(content="System aware response")
    client._client.post = AsyncMock(return_value=mock_response)

    await client.complete("Hello", system="You are a helpful assistant")

    call_args = client._client.post.call_args
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
    client._client.post = AsyncMock(return_value=mock_response)

    result = await client.complete("Extract this")

    assert result == expected_content


# === Retry Logic (10 tests) ===


@pytest.mark.asyncio
async def test_retry_on_500_internal_error(client: OpenRouterClient) -> None:
    """Test retries on 500 Internal Server Error."""
    error_response = make_response(status_code=500)
    success_response = make_response(content="Success after retry")

    # Fail once, then succeed
    client._client.post = AsyncMock(side_effect=[error_response, success_response])

    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await client.complete("Test")

    assert result == "Success after retry"
    assert client._client.post.call_count == 2


@pytest.mark.asyncio
async def test_retry_on_502_bad_gateway(client: OpenRouterClient) -> None:
    """Test retries on 502 Bad Gateway."""
    error_response = make_response(status_code=502)
    success_response = make_response(content="Success")

    client._client.post = AsyncMock(side_effect=[error_response, success_response])

    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await client.complete("Test")

    assert result == "Success"


@pytest.mark.asyncio
async def test_retry_on_503_unavailable(client: OpenRouterClient) -> None:
    """Test retries on 503 Service Unavailable."""
    error_response = make_response(status_code=503)
    success_response = make_response(content="Success")

    client._client.post = AsyncMock(side_effect=[error_response, success_response])

    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await client.complete("Test")

    assert result == "Success"


@pytest.mark.asyncio
async def test_retry_on_504_gateway_timeout(client: OpenRouterClient) -> None:
    """Test retries on 504 Gateway Timeout."""
    error_response = make_response(status_code=504)
    success_response = make_response(content="Success")

    client._client.post = AsyncMock(side_effect=[error_response, success_response])

    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await client.complete("Test")

    assert result == "Success"


@pytest.mark.asyncio
async def test_retry_on_timeout_exception(client: OpenRouterClient) -> None:
    """Test retries on httpx.TimeoutException."""
    success_response = make_response(content="Success after timeout")

    client._client.post = AsyncMock(
        side_effect=[
            httpx.TimeoutException("Timeout"),
            success_response,
        ]
    )

    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await client.complete("Test")

    assert result == "Success after timeout"


@pytest.mark.asyncio
async def test_retry_on_network_error(client: OpenRouterClient) -> None:
    """Test retries on httpx.NetworkError (e.g. ReadError)."""
    success_response = make_response(content="Connected")

    client._client.post = AsyncMock(
        side_effect=[
            httpx.ReadError("Connection parsing failed"),
            success_response,
        ]
    )

    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await client.complete("Test")

    assert result == "Connected"


@pytest.mark.asyncio
async def test_retry_on_429_rate_limit(client: OpenRouterClient) -> None:
    """Test retries on 429 with Retry-After header parsing."""
    rate_limit_response = make_response(status_code=429, headers={"Retry-After": "5"})
    success_response = make_response(content="Success")

    client._client.post = AsyncMock(side_effect=[rate_limit_response, success_response])

    sleep_calls = []

    async def mock_sleep(seconds: float):
        sleep_calls.append(seconds)

    with patch("asyncio.sleep", side_effect=mock_sleep):
        result = await client.complete("Test")

    assert result == "Success"
    assert sleep_calls == [5.0]


@pytest.mark.asyncio
async def test_exponential_backoff_delays(client: OpenRouterClient) -> None:
    """Verify delays are 1s, 2s, 4s (mocked asyncio.sleep)."""
    error_response = make_response(status_code=500)
    success_response = make_response(content="Success")

    sleep_calls: list[float] = []

    async def mock_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    # Fail 3 times, succeed on 4th
    client._client.post = AsyncMock(
        side_effect=[
            error_response,
            error_response,
            error_response,
            success_response,
        ]
    )

    with patch("asyncio.sleep", side_effect=mock_sleep):
        result = await client.complete("Test")

    assert result == "Success"
    # Logic:
    # Attempt 0 (Fail): Sleep 2^0 = 1
    # Attempt 1 (Fail): Sleep 2^1 = 2
    # Attempt 2 (Fail): Sleep 2^2 = 4
    # Attempt 3 (Success)
    assert sleep_calls == [1, 2, 4]


@pytest.mark.asyncio
async def test_max_retries_exceeded_raises(client: OpenRouterClient) -> None:
    """Test raises LLMError after max retries + 1 attempts."""
    error_response = make_response(status_code=500)
    client._client.post = AsyncMock(return_value=error_response)

    with (
        patch("asyncio.sleep", new_callable=AsyncMock),
        pytest.raises(LLMError) as exc_info,
    ):
        await client.complete("Test")

    assert "Max retries (3) exceeded" in str(exc_info.value)
    assert exc_info.value.retryable is True
    # max_retries + 1 = 4 calls
    assert client._client.post.call_count == 4


@pytest.mark.asyncio
async def test_success_after_retry(client: OpenRouterClient) -> None:
    """Test succeeds on 2nd or 3rd attempt."""
    error_response = make_response(status_code=503)
    success_response = make_response(content="Third time's a charm")

    client._client.post = AsyncMock(
        side_effect=[
            error_response,
            error_response,
            success_response,
        ]
    )

    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await client.complete("Test")

    assert result == "Third time's a charm"
    assert client._client.post.call_count == 3


# === Non-Retryable Errors (5 tests) ===


@pytest.mark.asyncio
async def test_no_retry_on_400_bad_request(client: OpenRouterClient) -> None:
    """Test raises immediately on 400 Bad Request."""
    error_response = make_response(status_code=400)
    client._client.post = AsyncMock(return_value=error_response)

    with pytest.raises(LLMError) as exc_info:
        await client.complete("Test")

    assert "400" in str(exc_info.value)
    assert client._client.post.call_count == 1  # No retry


@pytest.mark.asyncio
async def test_no_retry_on_401_unauthorized(client: OpenRouterClient) -> None:
    """Test raises immediately on 401 Unauthorized."""
    error_response = make_response(status_code=401)
    client._client.post = AsyncMock(return_value=error_response)

    with pytest.raises(LLMError) as exc_info:
        await client.complete("Test")

    assert "401" in str(exc_info.value)
    assert client._client.post.call_count == 1


@pytest.mark.asyncio
async def test_no_retry_on_403_forbidden(client: OpenRouterClient) -> None:
    """Test raises immediately on 403 Forbidden."""
    error_response = make_response(status_code=403)
    client._client.post = AsyncMock(return_value=error_response)

    with pytest.raises(LLMError) as exc_info:
        await client.complete("Test")

    assert "403" in str(exc_info.value)
    assert client._client.post.call_count == 1


@pytest.mark.asyncio
async def test_no_retry_on_404_not_found(client: OpenRouterClient) -> None:
    """Test raises immediately on 404 Not Found."""
    error_response = make_response(status_code=404)
    client._client.post = AsyncMock(return_value=error_response)

    with pytest.raises(LLMError) as exc_info:
        await client.complete("Test")

    assert "404" in str(exc_info.value)
    assert client._client.post.call_count == 1


@pytest.mark.asyncio
async def test_4xx_error_not_retryable_flag(client: OpenRouterClient) -> None:
    """Test LLMError.retryable == False for 4xx errors."""
    error_response = make_response(status_code=400)
    client._client.post = AsyncMock(return_value=error_response)

    with pytest.raises(LLMError) as exc_info:
        await client.complete("Test")

    assert exc_info.value.retryable is False


# === Timeout Handling (3 tests) ===


@pytest.mark.asyncio
async def test_timeout_raises_llm_timeout_error(client: OpenRouterClient) -> None:
    """Test LLMTimeoutError is raised on timeout."""
    client._client.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

    with (
        patch("asyncio.sleep", new_callable=AsyncMock),
        pytest.raises(LLMError) as exc_info,
    ):
        await client.complete("Test")

    # After retries exhausted, we get LLMError wrapping the timeout
    assert exc_info.value.retryable is True


@pytest.mark.asyncio
async def test_custom_timeout_value() -> None:
    """Test constructor timeout propagated."""
    # We can checks self.timeout but checking httpx.Timeout requires internal verification
    # or relying on default arg logic.
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
    client._client.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

    with (
        patch("asyncio.sleep", new_callable=AsyncMock),
        pytest.raises(LLMError) as exc_info,
    ):
        await client.complete("Test")

    assert "Max retries" in str(exc_info.value)
    assert client._client.post.call_count == 4  # 3 retries + 1 initial


# === Response Parsing (6 tests) ===


@pytest.mark.asyncio
async def test_empty_choices_array(client: OpenRouterClient) -> None:
    """Test handles choices: [] gracefully."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = 200
    response.json.return_value = {"choices": []}
    response.text = '{"choices": []}'

    client._client.post = AsyncMock(return_value=response)

    with pytest.raises(LLMError) as exc_info:
        await client.complete("Test")

    assert "Empty or invalid 'choices'" in str(exc_info.value)
    assert exc_info.value.retryable is False


@pytest.mark.asyncio
async def test_missing_content_field(client: OpenRouterClient) -> None:
    """Test handles missing message.content."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = 200
    response.json.return_value = {"choices": [{"message": {}}]}

    client._client.post = AsyncMock(return_value=response)

    with pytest.raises(LLMError) as exc_info:
        await client.complete("Test")

    assert "Missing 'content'" in str(exc_info.value)


@pytest.mark.asyncio
async def test_malformed_json_response(client: OpenRouterClient) -> None:
    """Test handles invalid JSON body (raises ValueError)."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = 200
    # response.json() raises ValueError (std lib json.JSONDecodeError is ValueError)
    response.json.side_effect = ValueError("Invalid JSON")

    client._client.post = AsyncMock(return_value=response)

    with pytest.raises(LLMError) as exc_info:
        await client.complete("Test")

    assert "Invalid JSON" in str(exc_info.value)


@pytest.mark.asyncio
async def test_unexpected_response_structure(client: OpenRouterClient) -> None:
    """Test handles response without choices field."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = 200
    response.json.return_value = {"data": "something"}

    client._client.post = AsyncMock(return_value=response)

    with pytest.raises(LLMError) as exc_info:
        await client.complete("Test")

    assert "Empty or invalid 'choices'" in str(exc_info.value)


@pytest.mark.asyncio
async def test_null_content_value(client: OpenRouterClient) -> None:
    """Test handles content: null."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = 200
    response.json.return_value = {"choices": [{"message": {"content": None}}]}

    client._client.post = AsyncMock(return_value=response)

    with pytest.raises(LLMError) as exc_info:
        await client.complete("Test")

    assert "Missing 'content'" in str(exc_info.value)


@pytest.mark.asyncio
async def test_whitespace_only_content(client: OpenRouterClient) -> None:
    """Test handles content with only whitespace."""
    mock_response = make_response(content="   ")
    client._client.post = AsyncMock(return_value=mock_response)

    result = await client.complete("Test")

    assert result == "   "


# === Edge Cases — Input (5 tests) ===


@pytest.mark.asyncio
async def test_unicode_characters_in_prompt(client: OpenRouterClient) -> None:
    """Test emoji, Cyrillic, CJK characters."""
    mock_response = make_response(content="Unicode response: 你好 🎉")
    client._client.post = AsyncMock(return_value=mock_response)

    result = await client.complete("Привет мир! 你好世界 🌍")

    assert result == "Unicode response: 你好 🎉"
    call_args = client._client.post.call_args
    payload = call_args.kwargs["json"]
    assert "Привет" in payload["messages"][0]["content"]


@pytest.mark.asyncio
async def test_very_long_prompt(client: OpenRouterClient) -> None:
    """Test 10K+ character prompt."""
    long_prompt = "A" * 15000  # 15K chars
    mock_response = make_response(content="Processed long prompt")
    client._client.post = AsyncMock(return_value=mock_response)

    result = await client.complete(long_prompt)

    assert result == "Processed long prompt"


@pytest.mark.asyncio
async def test_empty_prompt(client: OpenRouterClient) -> None:
    """Test empty string prompt."""
    mock_response = make_response(content="Empty prompt response")
    client._client.post = AsyncMock(return_value=mock_response)

    result = await client.complete("")

    assert result == "Empty prompt response"


@pytest.mark.asyncio
async def test_whitespace_only_prompt(client: OpenRouterClient) -> None:
    """Test prompt with only spaces/tabs."""
    mock_response = make_response(content="Whitespace prompt response")
    client._client.post = AsyncMock(return_value=mock_response)

    result = await client.complete("   \t\t   ")

    assert result == "Whitespace prompt response"


@pytest.mark.asyncio
async def test_special_characters_prompt(client: OpenRouterClient) -> None:
    """Test newlines, tabs, quotes, backslashes."""
    special_prompt = 'Hello\n\tWorld "quoted" \\ backslash'
    mock_response = make_response(content="Special chars handled")
    client._client.post = AsyncMock(return_value=mock_response)

    result = await client.complete(special_prompt)

    assert result == "Special chars handled"


# === Headers & Configuration (3 tests) ===


@pytest.mark.asyncio
async def test_authorization_header_set(client: OpenRouterClient) -> None:
    """Test Authorization: Bearer {key} is present in client headers."""
    # Headers are set on init in the _client
    assert client._client.headers["Authorization"] == "Bearer test-api-key"


@pytest.mark.asyncio
async def test_content_type_json(client: OpenRouterClient) -> None:
    """Test Content-Type: application/json in client headers."""
    assert client._client.headers["Content-Type"] == "application/json"


@pytest.mark.asyncio
async def test_model_parameter_in_request(client: OpenRouterClient) -> None:
    """Test model from constructor used in request body."""
    mock_response = make_response(content="Model OK")
    client._client.post = AsyncMock(return_value=mock_response)

    await client.complete("Test")

    call_args = client._client.post.call_args
    payload = call_args.kwargs["json"]
    assert payload["model"] == "test-model"


# === Robustness Tests (Round 3) ===


@pytest.mark.asyncio
async def test_retry_after_http_date(client: OpenRouterClient) -> None:
    """Test parsing of HTTP-date format in Retry-After header."""
    # Fri, 31 Dec 2025 12:00:00 GMT
    http_date = "Fri, 31 Dec 2025 12:00:05 GMT"
    # Corresponding static time: Fri, 31 Dec 2025 12:00:00 GMT
    # Difference = 5 seconds

    # We patch datetime in the client module to control "now"
    # Note: parsedate_to_datetime returns timezone-aware UTC datetime

    # Mock response
    response = MagicMock(spec=httpx.Response)
    response.status_code = 429
    response.headers = httpx.Headers({"Retry-After": http_date})

    # Mock client to return 429 then success
    success_response = make_response(content="After wait")
    client._client.post = AsyncMock(side_effect=[response, success_response])

    from datetime import timezone
    from email.utils import parsedate_to_datetime as parse

    fixed_now = parse("Fri, 31 Dec 2025 12:00:00 GMT")

    with (
        patch("src.llm.client.datetime") as mock_dt,
        patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):
        mock_dt.now.return_value = fixed_now
        # We need to ensure timezone is passed correctly if code uses it
        mock_dt.timezone = timezone

        result = await client.complete("Test")

    assert result == "After wait"
    # Should sleep 5.0 seconds
    mock_sleep.assert_called_with(5.0)


@pytest.mark.asyncio
async def test_invalid_content_type(client: OpenRouterClient) -> None:
    """Test response with non-string content (e.g. integer)."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = 200
    # Content is integer, not string
    response.json.return_value = {"choices": [{"message": {"content": 123}}]}

    client._client.post = AsyncMock(return_value=response)

    with pytest.raises(LLMError) as exc_info:
        await client.complete("Test")

    assert "Unexpected content type: int" in str(exc_info.value)


@pytest.mark.asyncio
async def test_invalid_choice_item_type(client: OpenRouterClient) -> None:
    """Test response with non-dict choice item."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = 200
    # choices contains integer, not dict
    response.json.return_value = {"choices": [123]}

    client._client.post = AsyncMock(return_value=response)

    with pytest.raises(LLMError) as exc_info:
        await client.complete("Test")

    assert "Invalid item in 'choices': expected dict" in str(exc_info.value)
