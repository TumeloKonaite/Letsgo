from __future__ import annotations

from datetime import timedelta
from io import BytesIO
from urllib.parse import quote, unquote, urlparse

from minio import Minio
from minio.error import InvalidResponseError, S3Error, ServerError
from urllib3.exceptions import HTTPError

from app.core.config import Settings
from app.domain.packages.storage import (
    StoredObject,
    StorageAuthenticationError,
    StorageBucketNotFoundError,
    StorageError,
    StorageService,
)


class MinioStorageService(StorageService):
    def __init__(
        self,
        *,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        secure: bool = False,
        client: Minio | None = None,
    ) -> None:
        self._endpoint = endpoint.strip().rstrip("/")
        self._bucket = bucket
        self._secure = secure
        self._client = client or Minio(
            self._endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )

    def upload_image(self, object_name: str, content: bytes, content_type: str) -> StoredObject:
        self._ensure_bucket_exists()
        try:
            self._client.put_object(
                bucket_name=self._bucket,
                object_name=object_name,
                data=BytesIO(content),
                length=len(content),
                content_type=content_type,
            )
        except (S3Error, InvalidResponseError, ServerError, HTTPError, OSError) as exc:
            self._raise_storage_error(exc)

        return StoredObject(
            object_name=object_name,
            url=self.get_public_url(object_name),
            content_type=content_type,
            size=len(content),
        )

    def upload_file(self, object_name: str, file_path: str, content_type: str) -> None:
        self._ensure_bucket_exists()
        try:
            self._client.fput_object(
                bucket_name=self._bucket,
                object_name=object_name,
                file_path=file_path,
                content_type=content_type,
            )
        except (S3Error, InvalidResponseError, ServerError, HTTPError, OSError) as exc:
            self._raise_storage_error(exc)

    def delete_image(self, object_name: str) -> None:
        self.delete_file(object_name)

    def delete_file(self, object_name: str) -> None:
        self._ensure_bucket_exists()
        try:
            self._client.remove_object(
                bucket_name=self._bucket,
                object_name=object_name,
            )
        except (S3Error, InvalidResponseError, ServerError, HTTPError, OSError) as exc:
            if isinstance(exc, S3Error) and exc.code == "NoSuchKey":
                return
            self._raise_storage_error(exc)

    def get_presigned_url(self, object_name: str, hours: int = 1) -> str:
        self._ensure_bucket_exists()
        try:
            return self._client.presigned_get_object(
                bucket_name=self._bucket,
                object_name=object_name,
                expires=timedelta(hours=hours),
            )
        except (S3Error, InvalidResponseError, ServerError, HTTPError, OSError) as exc:
            self._raise_storage_error(exc)

    def get_public_url(self, object_name: str) -> str:
        scheme = "https" if self._secure else "http"
        return f"{scheme}://{self._endpoint}/{self._bucket}/{quote(object_name, safe='/~')}"

    def extract_object_name(self, url: str) -> str | None:
        parsed = urlparse(url)
        expected_prefix = f"/{self._bucket}/"
        if not parsed.path.startswith(expected_prefix):
            return None
        return unquote(parsed.path[len(expected_prefix) :])

    def _ensure_bucket_exists(self) -> None:
        try:
            bucket_exists = self._client.bucket_exists(self._bucket)
        except (S3Error, InvalidResponseError, ServerError, HTTPError, OSError) as exc:
            self._raise_storage_error(exc)

        if not bucket_exists:
            raise StorageBucketNotFoundError(f"Storage bucket '{self._bucket}' was not found.")

    def _raise_storage_error(
        self,
        exc: S3Error | InvalidResponseError | ServerError | HTTPError | OSError,
    ) -> None:
        if isinstance(exc, S3Error):
            if exc.code in {"AccessDenied", "InvalidAccessKeyId", "SignatureDoesNotMatch"}:
                raise StorageAuthenticationError("Storage credentials were rejected.") from exc
            if exc.code == "NoSuchBucket":
                raise StorageBucketNotFoundError(
                    f"Storage bucket '{self._bucket}' was not found."
                ) from exc
            raise StorageError(f"Storage request failed: {exc.code}.") from exc

        raise StorageError(f"Storage request failed: {type(exc).__name__}.") from exc


def create_storage_service(settings: Settings) -> StorageService:
    provider = settings.storage_provider.strip().lower()
    if provider != "minio":
        raise ValueError(f"Unsupported storage provider: {settings.storage_provider}")

    return MinioStorageService(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        bucket=settings.minio_bucket,
        secure=settings.minio_secure,
    )
