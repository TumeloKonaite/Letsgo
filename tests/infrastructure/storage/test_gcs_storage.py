from __future__ import annotations

from dataclasses import dataclass, field

from google.api_core.exceptions import Forbidden, NotFound
import pytest

from app.domain.packages.storage import (
    StorageAuthenticationError,
    StorageBucketNotFoundError,
    StorageError,
)
from app.infrastructure.storage.gcs_storage import GcsStorageService


@dataclass
class FakeBlob:
    object_name: str
    uploads: list[tuple[str, bytes, int, str]] = field(default_factory=list)
    upload_error: Exception | None = None
    delete_error: Exception | None = None
    deleted: bool = False

    def upload_from_file(self, file_obj, *, size: int, content_type: str) -> None:
        if self.upload_error is not None:
            raise self.upload_error
        self.uploads.append((self.object_name, file_obj.read(), size, content_type))

    def delete(self) -> None:
        if self.delete_error is not None:
            raise self.delete_error
        self.deleted = True


@dataclass
class FakeBucket:
    name: str
    exists_result: bool = True
    exists_error: Exception | None = None
    blob_upload_error: Exception | None = None
    blob_delete_error: Exception | None = None
    blobs: dict[str, FakeBlob] = field(default_factory=dict)

    def exists(self) -> bool:
        if self.exists_error is not None:
            raise self.exists_error
        return self.exists_result

    def blob(self, object_name: str) -> FakeBlob:
        blob = self.blobs.setdefault(object_name, FakeBlob(object_name=object_name))
        blob.upload_error = self.blob_upload_error
        blob.delete_error = self.blob_delete_error
        return blob


@dataclass
class FakeGcsClient:
    bucket_instance: FakeBucket

    def bucket(self, bucket_name: str) -> FakeBucket:
        assert bucket_name == self.bucket_instance.name
        return self.bucket_instance


def _build_service(bucket: FakeBucket) -> GcsStorageService:
    return GcsStorageService(
        project_id="letsgodb",
        bucket_name="letsgosa-package-images",
        public_base_url="https://storage.googleapis.com/letsgosa-package-images",
        client=FakeGcsClient(bucket),
    )


def test_upload_image_succeeds() -> None:
    bucket = FakeBucket(name="letsgosa-package-images")
    storage = _build_service(bucket)

    stored_object = storage.upload_image(
        "packages/cape-town-tour/photo.jpg",
        b"\xff\xd8\xfftest",
        "image/jpeg",
    )

    assert bucket.blobs["packages/cape-town-tour/photo.jpg"].uploads == [
        ("packages/cape-town-tour/photo.jpg", b"\xff\xd8\xfftest", 7, "image/jpeg")
    ]
    assert stored_object.url == (
        "https://storage.googleapis.com/letsgosa-package-images/packages/cape-town-tour/photo.jpg"
    )


def test_delete_image_succeeds() -> None:
    bucket = FakeBucket(name="letsgosa-package-images")
    storage = _build_service(bucket)

    storage.delete_image("packages/cape-town-tour/photo.jpg")

    assert bucket.blobs["packages/cape-town-tour/photo.jpg"].deleted is True


def test_invalid_credentials_fail_gracefully() -> None:
    bucket = FakeBucket(
        name="letsgosa-package-images", exists_error=Forbidden("denied")
    )
    storage = _build_service(bucket)

    with pytest.raises(StorageAuthenticationError):
        storage.upload_image(
            "packages/cape-town-tour/photo.jpg",
            b"\xff\xd8\xfftest",
            "image/jpeg",
        )


def test_missing_bucket_returns_specific_error() -> None:
    bucket = FakeBucket(name="letsgosa-package-images", exists_result=False)
    storage = _build_service(bucket)

    with pytest.raises(StorageBucketNotFoundError):
        storage.upload_image(
            "packages/cape-town-tour/photo.jpg",
            b"\x89PNG\r\n\x1a\ntest",
            "image/png",
        )


def test_extract_object_name_supports_public_bucket_urls() -> None:
    bucket = FakeBucket(name="letsgosa-package-images")
    storage = _build_service(bucket)

    assert (
        storage.extract_object_name(
            "https://storage.googleapis.com/letsgosa-package-images/packages/cape-town-tour/photo.jpg"
        )
        == "packages/cape-town-tour/photo.jpg"
    )


def test_network_errors_are_wrapped_as_storage_errors() -> None:
    bucket = FakeBucket(
        name="letsgosa-package-images", exists_error=OSError("connection refused")
    )
    storage = _build_service(bucket)

    with pytest.raises(StorageError, match="Storage request failed: OSError."):
        storage.upload_image("packages/cape-town-tour/photo.jpg", b"data", "image/jpeg")


def test_missing_object_delete_is_ignored() -> None:
    bucket = FakeBucket(
        name="letsgosa-package-images", blob_delete_error=NotFound("missing")
    )
    storage = _build_service(bucket)

    storage.delete_image("packages/cape-town-tour/photo.jpg")
