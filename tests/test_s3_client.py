"""Unit tests for S3Client (Phase 8b).

These tests mock the underlying aiobotocore client to test S3Client logic
without network calls. Real S3/MinIO testing is done in E2E tests.

Note: moto doesn't fully support aiobotocore async operations,
so we mock at the aiobotocore client level instead.
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

# Test credentials - stored as constants
TEST_AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID", "testing")
TEST_AWS_SECRET_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "testing")
TEST_REGION = "us-east-1"
TEST_BUCKET = "test-bucket"


@pytest.fixture(autouse=True)
def mock_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock settings for all tests in this module."""
    monkeypatch.setenv("ALLOWED_USER_ID", "123456")
    monkeypatch.setenv("POSTGRES_URL", "postgresql+asyncpg://test@localhost/test")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("GEMINI_GATEWAY_URL", "http://localhost:8080")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
    monkeypatch.setenv("LLM_API_KEY", "test_key")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS_JSON", "e30=")  # base64 {}
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")
    monkeypatch.setenv("S3_ACCESS_KEY", TEST_AWS_ACCESS_KEY)
    monkeypatch.setenv("S3_SECRET_KEY", TEST_AWS_SECRET_KEY)
    monkeypatch.setenv("S3_ENDPOINT", "http://localhost:9000")
    monkeypatch.setenv("S3_BUCKET", TEST_BUCKET)

    # Clear cached settings
    from src.api.settings import get_settings

    get_settings.cache_clear()


TEST_USER_ID = 12345
TEST_SESSION_ID = UUID("12345678-1234-5678-1234-567812345678")
TEST_CONTENT = b"Hello, World!"
TEST_FILENAME = "test.txt"
TEST_CONTENT_TYPE = "text/plain"


@pytest.fixture
def mock_aiobotocore_session():
    """Mock aiobotocore session and client."""
    mock_client = AsyncMock()

    # Mock context manager behavior
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    # Mock S3 operations
    mock_client.put_object = AsyncMock(return_value={})
    mock_client.delete_object = AsyncMock(return_value={})
    mock_client.head_bucket = AsyncMock(return_value={})
    mock_client.generate_presigned_url = AsyncMock(
        return_value=f"https://s3.{TEST_REGION}.amazonaws.com/{TEST_BUCKET}/test-key?X-Amz-Signature=test"
    )

    mock_session = MagicMock()
    mock_session.create_client.return_value = mock_client

    return mock_session, mock_client


class TestS3ClientUpload:
    """Tests for upload_attachment method."""

    async def test_upload_attachment_success(self, mock_aiobotocore_session) -> None:
        """Upload succeeds and returns valid S3 key."""
        mock_session, mock_client = mock_aiobotocore_session

        with patch("src.storage.s3_client.get_session", return_value=mock_session):
            from src.storage.s3_client import S3Client

            client = S3Client(
                endpoint=None,
                bucket=TEST_BUCKET,
                access_key=TEST_AWS_ACCESS_KEY,
                secret_key=TEST_AWS_SECRET_KEY,
                region=TEST_REGION,
            )

            async with client:
                key = await client.upload_attachment(
                    user_id=TEST_USER_ID,
                    session_id=TEST_SESSION_ID,
                    content=TEST_CONTENT,
                    filename=TEST_FILENAME,
                    content_type=TEST_CONTENT_TYPE,
                )

            # Verify key format: attachments/{user_id}/{session_id}/{uuid}.{ext}
            assert key.startswith(f"attachments/{TEST_USER_ID}/{TEST_SESSION_ID}/")
            assert key.endswith(".txt")

            # Verify put_object was called
            mock_client.put_object.assert_called_once()
            call_kwargs = mock_client.put_object.call_args.kwargs
            assert call_kwargs["Bucket"] == TEST_BUCKET
            assert call_kwargs["Body"] == TEST_CONTENT
            assert call_kwargs["ContentType"] == TEST_CONTENT_TYPE

    async def test_upload_generates_unique_keys(self, mock_aiobotocore_session) -> None:
        """Two uploads generate different keys."""
        mock_session, _mock_client = mock_aiobotocore_session

        with patch("src.storage.s3_client.get_session", return_value=mock_session):
            from src.storage.s3_client import S3Client

            client = S3Client(
                endpoint=None,
                bucket=TEST_BUCKET,
                access_key=TEST_AWS_ACCESS_KEY,
                secret_key=TEST_AWS_SECRET_KEY,
                region=TEST_REGION,
            )

            async with client:
                key1 = await client.upload_attachment(
                    user_id=TEST_USER_ID,
                    session_id=TEST_SESSION_ID,
                    content=TEST_CONTENT,
                    filename=TEST_FILENAME,
                    content_type=TEST_CONTENT_TYPE,
                )
                key2 = await client.upload_attachment(
                    user_id=TEST_USER_ID,
                    session_id=TEST_SESSION_ID,
                    content=TEST_CONTENT,
                    filename=TEST_FILENAME,
                    content_type=TEST_CONTENT_TYPE,
                )

            assert key1 != key2


class TestS3ClientPresignedUrl:
    """Tests for generate_presigned_url method."""

    async def test_generate_presigned_url(self, mock_aiobotocore_session) -> None:
        """Presigned URL is generated with correct parameters."""
        mock_session, mock_client = mock_aiobotocore_session

        with patch("src.storage.s3_client.get_session", return_value=mock_session):
            from src.storage.s3_client import S3Client

            client = S3Client(
                endpoint=None,
                bucket=TEST_BUCKET,
                access_key=TEST_AWS_ACCESS_KEY,
                secret_key=TEST_AWS_SECRET_KEY,
                region=TEST_REGION,
            )

            test_key = "test/file.txt"

            async with client:
                url = await client.generate_presigned_url(test_key)

            # URL should be returned from mock
            assert "X-Amz-Signature" in url

            # Verify generate_presigned_url was called with correct params
            mock_client.generate_presigned_url.assert_called_once_with(
                "get_object",
                Params={"Bucket": TEST_BUCKET, "Key": test_key},
                ExpiresIn=3600,  # Default TTL
            )

    async def test_presigned_url_custom_ttl(self, mock_aiobotocore_session) -> None:
        """Presigned URL respects custom TTL."""
        mock_session, mock_client = mock_aiobotocore_session

        with patch("src.storage.s3_client.get_session", return_value=mock_session):
            from src.storage.s3_client import S3Client

            client = S3Client(
                endpoint=None,
                bucket=TEST_BUCKET,
                access_key=TEST_AWS_ACCESS_KEY,
                secret_key=TEST_AWS_SECRET_KEY,
                region=TEST_REGION,
                presigned_ttl=7200,
            )

            test_key = "test/file.txt"

            async with client:
                await client.generate_presigned_url(test_key, expires_in=1800)

            # Verify custom TTL was passed
            mock_client.generate_presigned_url.assert_called_once_with(
                "get_object",
                Params={"Bucket": TEST_BUCKET, "Key": test_key},
                ExpiresIn=1800,
            )


class TestS3ClientDelete:
    """Tests for delete_attachment method."""

    async def test_delete_attachment(self, mock_aiobotocore_session) -> None:
        """Delete removes object from S3."""
        mock_session, mock_client = mock_aiobotocore_session

        with patch("src.storage.s3_client.get_session", return_value=mock_session):
            from src.storage.s3_client import S3Client

            client = S3Client(
                endpoint=None,
                bucket=TEST_BUCKET,
                access_key=TEST_AWS_ACCESS_KEY,
                secret_key=TEST_AWS_SECRET_KEY,
                region=TEST_REGION,
            )

            test_key = "test/to_delete.txt"

            async with client:
                result = await client.delete_attachment(test_key)

            assert result is True
            mock_client.delete_object.assert_called_once_with(Bucket=TEST_BUCKET, Key=test_key)


class TestS3ClientHealthCheck:
    """Tests for check_health method."""

    async def test_check_health_success(self, mock_aiobotocore_session) -> None:
        """Health check returns True when bucket exists."""
        mock_session, mock_client = mock_aiobotocore_session

        with patch("src.storage.s3_client.get_session", return_value=mock_session):
            from src.storage.s3_client import S3Client

            client = S3Client(
                endpoint=None,
                bucket=TEST_BUCKET,
                access_key=TEST_AWS_ACCESS_KEY,
                secret_key=TEST_AWS_SECRET_KEY,
                region=TEST_REGION,
            )

            async with client:
                result = await client.check_health()

            assert result is True
            mock_client.head_bucket.assert_called_once_with(Bucket=TEST_BUCKET)

    async def test_check_health_failure_bucket_missing(self, mock_aiobotocore_session) -> None:
        """Health check returns False when bucket doesn't exist."""
        mock_session, mock_client = mock_aiobotocore_session

        # Make head_bucket raise an exception
        mock_client.head_bucket = AsyncMock(side_effect=Exception("NoSuchBucket"))

        with patch("src.storage.s3_client.get_session", return_value=mock_session):
            from src.storage.s3_client import S3Client

            client = S3Client(
                endpoint=None,
                bucket="nonexistent-bucket",
                access_key=TEST_AWS_ACCESS_KEY,
                secret_key=TEST_AWS_SECRET_KEY,
                region=TEST_REGION,
            )

            async with client:
                result = await client.check_health()

            assert result is False


class TestS3ClientRetry:
    """Tests for retry logic."""

    async def test_retry_on_transient_failure(self, mock_aiobotocore_session) -> None:
        """Client retries on transient failures (ClientError)."""
        from botocore.exceptions import ClientError

        mock_session, mock_client = mock_aiobotocore_session

        call_count = 0

        async def failing_put_object(**_kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ClientError(
                    {"Error": {"Code": "ServiceUnavailable", "Message": "Transient"}},
                    "PutObject",
                )
            return {}

        mock_client.put_object = AsyncMock(side_effect=failing_put_object)

        with patch("src.storage.s3_client.get_session", return_value=mock_session):
            from src.storage.s3_client import S3Client

            client = S3Client(
                endpoint=None,
                bucket=TEST_BUCKET,
                access_key=TEST_AWS_ACCESS_KEY,
                secret_key=TEST_AWS_SECRET_KEY,
                region=TEST_REGION,
            )

            async with client:
                key = await client.upload_attachment(
                    user_id=TEST_USER_ID,
                    session_id=TEST_SESSION_ID,
                    content=TEST_CONTENT,
                    filename=TEST_FILENAME,
                    content_type=TEST_CONTENT_TYPE,
                )

            assert key is not None
            assert call_count == 2  # First call failed, second succeeded

    async def test_retry_exhausted_raises_error(self, mock_aiobotocore_session) -> None:
        """Client raises error after all retries exhausted."""
        from botocore.exceptions import ClientError

        mock_session, mock_client = mock_aiobotocore_session

        # Always fail with ClientError
        mock_client.put_object = AsyncMock(
            side_effect=ClientError(
                {"Error": {"Code": "InternalError", "Message": "Persistent"}},
                "PutObject",
            )
        )

        with patch("src.storage.s3_client.get_session", return_value=mock_session):
            from src.storage.s3_client import S3Client, S3UploadError

            client = S3Client(
                endpoint=None,
                bucket=TEST_BUCKET,
                access_key=TEST_AWS_ACCESS_KEY,
                secret_key=TEST_AWS_SECRET_KEY,
                region=TEST_REGION,
            )

            async with client:
                with pytest.raises(S3UploadError) as exc_info:
                    await client.upload_attachment(
                        user_id=TEST_USER_ID,
                        session_id=TEST_SESSION_ID,
                        content=TEST_CONTENT,
                        filename=TEST_FILENAME,
                        content_type=TEST_CONTENT_TYPE,
                    )

            assert "Persistent" in str(exc_info.value)
            assert mock_client.put_object.call_count == 3  # MAX_RETRIES


class TestS3ClientNotInitialized:
    """Tests for error handling when client not initialized."""

    async def test_upload_without_context_manager_raises(self) -> None:
        """Upload without context manager raises S3Error."""
        from src.storage.s3_client import S3Client, S3Error

        client = S3Client(
            endpoint=None,
            bucket=TEST_BUCKET,
            access_key=TEST_AWS_ACCESS_KEY,
            secret_key=TEST_AWS_SECRET_KEY,
            region=TEST_REGION,
        )

        with pytest.raises(S3Error, match="not initialized"):
            await client.upload_attachment(
                user_id=TEST_USER_ID,
                session_id=TEST_SESSION_ID,
                content=TEST_CONTENT,
                filename=TEST_FILENAME,
                content_type=TEST_CONTENT_TYPE,
            )
