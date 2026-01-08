"""E2E tests for S3 attachment storage (Phase 8b).

These tests connect to real MinIO (teeshka-e2e bucket).

Run with: pytest -m e2e tests/e2e/test_s3.py
"""

import httpx
import pytest
import uuid_utils

TEST_CONTENT = b"E2E test file content - " + uuid_utils.uuid7().bytes
TEST_FILENAME = "e2e_test.txt"
TEST_CONTENT_TYPE = "text/plain"


@pytest.mark.e2e
class TestS3E2E:
    """E2E tests for S3 storage."""

    async def test_e2e_upload_and_download(self, e2e_s3_client) -> None:
        """Upload file, get presigned URL, download and verify content.

        Full cycle test:
        1. Upload attachment to MinIO
        2. Generate presigned URL
        3. Download via presigned URL
        4. Verify content matches
        5. Cleanup: delete the file
        """
        user_id = 999999
        session_id = uuid_utils.uuid7()

        # Upload
        key = await e2e_s3_client.upload_attachment(
            user_id=user_id,
            session_id=session_id,
            content=TEST_CONTENT,
            filename=TEST_FILENAME,
            content_type=TEST_CONTENT_TYPE,
        )

        # Verify key format
        assert key.startswith(f"attachments/{user_id}/{session_id}/")
        assert key.endswith(".txt")

        # Generate presigned URL
        presigned_url = await e2e_s3_client.generate_presigned_url(key)
        assert presigned_url is not None
        assert "X-Amz-Signature" in presigned_url or "Signature" in presigned_url

        # Download via presigned URL
        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(presigned_url)
            assert response.status_code == 200
            assert response.content == TEST_CONTENT

        # Cleanup
        deleted = await e2e_s3_client.delete_attachment(key)
        assert deleted is True

    async def test_e2e_delete_cleanup(self, e2e_s3_client) -> None:
        """Upload file, delete it, verify it's gone.

        Test delete functionality:
        1. Upload a file
        2. Delete the file
        3. Try to access presigned URL - should fail or return error
        """
        user_id = 888888
        session_id = uuid_utils.uuid7()
        test_content = b"File to be deleted - " + uuid_utils.uuid7().bytes

        # Upload
        key = await e2e_s3_client.upload_attachment(
            user_id=user_id,
            session_id=session_id,
            content=test_content,
            filename="to_delete.txt",
            content_type="text/plain",
        )

        # Delete
        deleted = await e2e_s3_client.delete_attachment(key)
        assert deleted is True

        # Generate presigned URL for deleted object
        presigned_url = await e2e_s3_client.generate_presigned_url(key)

        # Try to download - should get 404 or similar error
        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(presigned_url)
            # MinIO returns 404 for deleted objects
            assert response.status_code in (404, 403)

    async def test_e2e_health_check(self, e2e_s3_client) -> None:
        """Verify S3 health check works with real MinIO."""
        result = await e2e_s3_client.check_health()
        assert result is True
