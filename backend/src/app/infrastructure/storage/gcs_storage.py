from __future__ import annotations

from collections.abc import Callable
from io import BytesIO
from urllib.parse import quote, unquote, urlparse

from google.api_core.exceptions import Forbidden, GoogleAPIError, NotFound, Unauthorized
from google.cloud.storage import Bucket, Client

from app.core.config import Settings
from app.domain.packages.storage import (
    StorageAuthenticationError,
    StorageBucketNotFoundError,
    StorageError,
    StorageService,
    StoredObject,
)


class GcsStorageService(StorageService):
    def __init__(
        self,
        *,
        project_id: str,
        bucket_name: str,
        public_base_url: str,
        client: Client | None = None,
        client_factory: Callable[[], Client] | None = None,
    ) -> None:
        self._project_id = project_id.strip()
        self._bucket_name = bucket_name.strip()
        self._public_base_url = public_base_url.rstrip("/")
        self._client = client
        self._client_factory = client_factory or (
            lambda: Client(project=self._project_id)
        )

    def _get_client(self) -> Client:
        if self._client is None:
            self._client = self._client_factory()
        return self._client

    def upload_image(
        self, object_name: str, content: bytes, content_type: str
    ) -> StoredObject:
        bucket = self._ensure_bucket_exists()
        blob = bucket.blob(object_name)
        try:
            blob.upload_from_file(
                BytesIO(content),
                size=len(content),
                content_type=content_type,
            )
        except (Forbidden, Unauthorized) as exc:
            raise StorageAuthenticationError(
                "Storage credentials were rejected."
            ) from exc
        except NotFound as exc:
            raise StorageBucketNotFoundError(
                f"Storage bucket '{self._bucket_name}' was not found."
            ) from exc
        except (GoogleAPIError, OSError) as exc:
            raise StorageError(
                f"Storage request failed: {type(exc).__name__}."
            ) from exc

        return StoredObject(
            object_name=object_name,
            url=self.get_public_url(object_name),
            content_type=content_type,
            size=len(content),
        )

    def delete_image(self, object_name: str) -> None:
        bucket = self._ensure_bucket_exists()
        blob = bucket.blob(object_name)
        try:
            blob.delete()
        except NotFound:
            return
        except (Forbidden, Unauthorized) as exc:
            raise StorageAuthenticationError(
                "Storage credentials were rejected."
            ) from exc
        except (GoogleAPIError, OSError) as exc:
            raise StorageError(
                f"Storage request failed: {type(exc).__name__}."
            ) from exc

    def get_public_url(self, object_name: str) -> str:
        return f"{self._public_base_url}/{quote(object_name, safe='/~')}"

    def extract_object_name(self, url: str) -> str | None:
        normalized_base = self._public_base_url.rstrip("/") + "/"
        if url.startswith(normalized_base):
            return unquote(url.removeprefix(normalized_base))

        parsed = urlparse(url)
        if parsed.netloc == "storage.googleapis.com":
            expected_prefix = f"/{self._bucket_name}/"
            if parsed.path.startswith(expected_prefix):
                return unquote(parsed.path[len(expected_prefix) :])
            return None

        if parsed.netloc == f"{self._bucket_name}.storage.googleapis.com":
            return unquote(parsed.path.lstrip("/"))

        return None

    def _ensure_bucket_exists(self) -> Bucket:
        bucket = self._get_client().bucket(self._bucket_name)
        try:
            if not bucket.exists():
                raise StorageBucketNotFoundError(
                    f"Storage bucket '{self._bucket_name}' was not found."
                )
        except (Forbidden, Unauthorized) as exc:
            raise StorageAuthenticationError(
                "Storage credentials were rejected."
            ) from exc
        except NotFound as exc:
            raise StorageBucketNotFoundError(
                f"Storage bucket '{self._bucket_name}' was not found."
            ) from exc
        except (GoogleAPIError, OSError) as exc:
            raise StorageError(
                f"Storage request failed: {type(exc).__name__}."
            ) from exc
        return bucket


def create_storage_service(settings: Settings) -> StorageService:
    provider = settings.storage_provider.strip().lower()
    if provider != "gcs":
        raise ValueError(f"Unsupported storage provider: {settings.storage_provider}")

    if (
        settings.gcp_project_id is None
        or settings.gcs_bucket_name is None
        or settings.gcs_public_base_url is None
    ):
        raise ValueError(
            "GCS storage settings must be configured before creating the storage service."
        )

    return GcsStorageService(
        project_id=settings.gcp_project_id,
        bucket_name=settings.gcs_bucket_name,
        public_base_url=settings.gcs_public_base_url,
    )
