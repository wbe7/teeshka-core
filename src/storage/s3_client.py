"""Async S3 client for attachment storage (GEMINI.md §3.8).

This module provides async S3 operations for storing and retrieving attachments.
All operations use retry logic with exponential backoff per GEMINI.md §3.6.

Key Format: attachments/{user_id}/{session_id}/{uuid}.{ext}
"""

import asyncio
import mimetypes
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar
from uuid import UUID

import structlog
import uuid_utils
from aiobotocore.session import get_session
from botocore.exceptions import ClientError, EndpointConnectionError

from src.api.settings import get_settings

T = TypeVar("T")

if TYPE_CHECKING:
    from types_aiobotocore_s3 import S3Client as S3ClientType

log = structlog.get_logger()

# Retry configuration per GEMINI.md §3.6
MAX_RETRIES = 3
INITIAL_BACKOFF_MS = 100


class S3Error(Exception):
    """Base exception for S3 operations."""

    pass


class S3UploadError(S3Error):
    """Raised when upload fails after all retries."""

    pass


class S3DeleteError(S3Error):
    """Raised when delete fails after all retries."""

    pass


class S3Client:
    """Async S3 client for attachment storage.

    All operations use retry logic (exponential backoff, max 3 attempts)
    per GEMINI.md §3.6.

    Usage:
        async with S3Client() as client:
            key = await client.upload_attachment(...)
            url = await client.generate_presigned_url(key)
    """

    def __init__(
        self,
        *,
        endpoint: str | None = ...,  # type: ignore[assignment]  # Sentinel for "use settings"
        bucket: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        region: str | None = None,
        presigned_ttl: int | None = None,
    ) -> None:
        """Initialize S3 client.

        Args:
            endpoint: S3 endpoint URL. Use None explicitly to skip endpoint (for moto tests).
                     Default (unspecified) uses settings.s3_endpoint.
            bucket: Bucket name. Defaults to settings.s3_bucket.
            access_key: Access key. Defaults to settings.s3_access_key.
            secret_key: Secret key. Defaults to settings.s3_secret_key.
            region: AWS region. Defaults to settings.s3_region.
            presigned_ttl: Presigned URL TTL in seconds. Defaults to settings.s3_presigned_ttl.
        """
        settings = get_settings()

        # Handle endpoint: ... = use settings, None = no endpoint (moto), str = explicit
        if endpoint is ...:
            self._endpoint = settings.s3_endpoint
        else:
            self._endpoint = endpoint  # Can be None for moto

        self._bucket = bucket if bucket is not None else settings.s3_bucket
        self._access_key = (
            access_key if access_key is not None else settings.s3_access_key.get_secret_value()
        )
        self._secret_key = (
            secret_key if secret_key is not None else settings.s3_secret_key.get_secret_value()
        )
        self._region = region if region is not None else settings.s3_region
        self._presigned_ttl = (
            presigned_ttl if presigned_ttl is not None else settings.s3_presigned_ttl
        )

        self._session = get_session()
        self._client: S3ClientType | None = None

    async def __aenter__(self) -> "S3Client":
        """Enter async context manager."""
        self._client = await self._session.create_client(
            "s3",
            endpoint_url=self._endpoint,
            region_name=self._region,
            aws_access_key_id=self._access_key,
            aws_secret_access_key=self._secret_key,
        ).__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context manager."""
        if self._client:
            await self._client.__aexit__(exc_type, exc_val, exc_tb)
            self._client = None

    async def _retry_operation(self, operation_name: str, func: Callable[[], Awaitable[T]]) -> T:
        """Execute operation with exponential backoff retry.

        Args:
            operation_name: Name for logging
            func: Async function to execute (no args, use closure)

        Returns:
            Result from func

        Raises:
            S3Error: If all retries exhausted
        """
        last_exception: Exception | None = None
        backoff_ms = INITIAL_BACKOFF_MS

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return await func()
            except (ClientError, EndpointConnectionError, TimeoutError) as e:
                last_exception = e
                if attempt < MAX_RETRIES:
                    log.warning(
                        "s3_operation_retry",
                        operation=operation_name,
                        attempt=attempt,
                        backoff_ms=backoff_ms,
                        error=str(e),
                    )
                    await asyncio.sleep(backoff_ms / 1000)
                    backoff_ms *= 2  # Exponential backoff

        log.error(
            "s3_operation_failed",
            operation=operation_name,
            attempts=MAX_RETRIES,
            error=str(last_exception),
        )
        raise S3Error(
            f"{operation_name} failed after {MAX_RETRIES} attempts: {last_exception}"
        ) from last_exception

    def _generate_s3_key(
        self,
        user_id: int,
        session_id: UUID,
        filename: str,
        content_type: str,
    ) -> str:
        """Generate S3 key per GEMINI.md §3.8 format.

        Format: attachments/{user_id}/{session_id}/{uuid}.{ext}

        Uses filename suffix first, falls back to content_type guessing.
        """
        # Get extension from filename, fallback to content_type, normalize to lowercase
        ext_from_filename = Path(filename).suffix
        ext_from_content_type = (
            mimetypes.guess_extension(content_type) if not ext_from_filename else None
        )
        ext = (ext_from_filename or ext_from_content_type or "").lower()

        unique_id = uuid_utils.uuid7()
        return f"attachments/{user_id}/{session_id}/{unique_id}{ext}"

    async def upload_attachment(
        self,
        user_id: int,
        session_id: UUID,
        content: bytes,
        filename: str,
        content_type: str,
    ) -> str:
        """Upload attachment to S3.

        Args:
            user_id: User ID for key path
            session_id: Session ID for key path
            content: File content as bytes
            filename: Original filename (used for extension)
            content_type: MIME type

        Returns:
            S3 key of uploaded object

        Raises:
            S3UploadError: If upload fails after retries
        """
        if not self._client:
            raise S3Error("S3Client not initialized. Use async context manager.")

        key = self._generate_s3_key(user_id, session_id, filename, content_type)

        async def _do_upload() -> str:
            await self._client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=content,
                ContentType=content_type,
            )
            return key

        try:
            result = await self._retry_operation("upload_attachment", _do_upload)
            log.info(
                "s3_upload_success",
                key=key,
                size=len(content),
                content_type=content_type,
            )
            return result
        except S3Error as e:
            raise S3UploadError(str(e)) from e

    async def generate_presigned_url(
        self,
        key: str,
        expires_in: int | None = None,
    ) -> str:
        """Generate presigned GET URL for S3 object.

        Args:
            key: S3 object key
            expires_in: URL expiry in seconds. Defaults to s3_presigned_ttl (3600).

        Returns:
            Presigned URL string
        """
        if not self._client:
            raise S3Error("S3Client not initialized. Use async context manager.")

        ttl = expires_in or self._presigned_ttl

        url = await self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=ttl,
        )

        log.debug("s3_presigned_url_generated", key=key, expires_in=ttl)
        return url

    async def delete_attachment(self, key: str) -> bool:
        """Delete attachment from S3.

        Used primarily for E2E test cleanup.

        Args:
            key: S3 object key

        Returns:
            True if deleted successfully

        Raises:
            S3DeleteError: If delete fails after retries
        """
        if not self._client:
            raise S3Error("S3Client not initialized. Use async context manager.")

        async def _do_delete() -> bool:
            await self._client.delete_object(Bucket=self._bucket, Key=key)
            return True

        try:
            result = await self._retry_operation("delete_attachment", _do_delete)
            log.info("s3_delete_success", key=key)
            return result
        except S3Error as e:
            raise S3DeleteError(str(e)) from e

    async def check_health(self) -> bool:
        """Check S3 connectivity by verifying bucket exists.

        Returns:
            True if bucket accessible, False otherwise
        """
        if not self._client:
            return False

        try:
            await self._client.head_bucket(Bucket=self._bucket)
            return True
        except (ClientError, EndpointConnectionError) as e:
            log.warning("s3_health_check_failed", bucket=self._bucket, error=str(e))
            return False


async def get_s3_client():
    """Async generator for FastAPI dependency injection.

    Usage:
        @app.post("/upload")
        async def endpoint(client: S3Client = Depends(get_s3_client)):
            await client.upload_attachment(...)

    Yields:
        Configured and connected S3Client instance
    """
    async with S3Client() as client:
        yield client
