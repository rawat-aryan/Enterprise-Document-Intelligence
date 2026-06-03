from __future__ import annotations

import logging
from typing import Optional

from backend.app.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from google.cloud import storage
                self._client = storage.Client(project=settings.GOOGLE_PROJECT_ID)
            except Exception as e:
                logger.warning(f"GCS client unavailable: {e}")
        return self._client

    async def upload_file(self, file_bytes: bytes, destination: str, content_type: str = "application/octet-stream") -> Optional[str]:
        client = self._get_client()
        if not client:
            logger.info(f"GCS unavailable, skipping upload for {destination}")
            return None
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._sync_upload, client, file_bytes, destination, content_type)
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return None

    def _sync_upload(self, client, file_bytes: bytes, destination: str, content_type: str) -> str:
        bucket = client.bucket(settings.GCS_BUCKET_NAME)
        blob = bucket.blob(destination)
        blob.upload_from_string(file_bytes, content_type=content_type)
        return f"gs://{settings.GCS_BUCKET_NAME}/{destination}"

    async def download_file(self, gcs_path: str) -> Optional[bytes]:
        client = self._get_client()
        if not client:
            return None
        try:
            import asyncio
            path = gcs_path.replace(f"gs://{settings.GCS_BUCKET_NAME}/", "")
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._sync_download, client, path)
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return None

    def _sync_download(self, client, path: str) -> bytes:
        bucket = client.bucket(settings.GCS_BUCKET_NAME)
        blob = bucket.blob(path)
        return blob.download_as_bytes()

    def generate_signed_url(self, gcs_path: str, expiration_minutes: int = 60) -> Optional[str]:
        client = self._get_client()
        if not client:
            return None
        try:
            from datetime import timedelta
            path = gcs_path.replace(f"gs://{settings.GCS_BUCKET_NAME}/", "")
            bucket = client.bucket(settings.GCS_BUCKET_NAME)
            blob = bucket.blob(path)
            return blob.generate_signed_url(expiration=timedelta(minutes=expiration_minutes), method="GET")
        except Exception as e:
            logger.error(f"Signed URL generation failed: {e}")
            return None


storage_service = StorageService()
