from __future__ import annotations

from dataclasses import dataclass, field

import pytest
from minio.error import S3Error

from app.domain.packages.storage import (
    StorageAuthenticationError,
    StorageBucketNotFoundError,
)
from app.infrastructure.storage.minio_storage import MinioStorageService


def _s3_error(code: str) -> S3Error:
    return S3Error(
        response=None,
        code=code,
        message=code,
        resource=None,
        request_id=None,
        host_id=None,
    )


@dataclass
class FakeMinioClient:
    bucket_exists_result: bool = True
    put_calls: list[tuple[str, str, bytes, int, str]] = field(default_factory=list)
    remove_calls: list[tuple[str, str]] = field(default_factory=list)
    presigned_calls: list[tuple[str, str, object]] = field(default_factory=list)
    fput_calls: list[tuple[str, str, str, str]] = field(default_factory=list)
    bucket_exists_error: Exception | None = None
    put_error: Exception | None = None
    remove_error: Exception | None = None
    presigned_error: Exception | None = None
    fput_error: Exception | None = None

    def bucket_exists(self, bucket_name: str) -> bool:
        if self.bucket_exists_error is not None:
            raise self.bucket_exists_error
        assert bucket_name == "package-images"
        return self.bucket_exists_result

    def put_object(self, bucket_name: str, object_name: str, data, length: int, content_type: str) -> None:
        if self.put_error is not None:
            raise self.put_error
        self.put_calls.append((bucket_name, object_name, data.read(), length, content_type))

    def fput_object(
        self,
        bucket_name: str,
        object_name: str,
        file_path: str,
        content_type: str,
    ) -> None:
        if self.fput_error is not None:
            raise self.fput_error
        self.fput_calls.append((bucket_name, object_name, file_path, content_type))

    def remove_object(self, bucket_name: str, object_name: str) -> None:
        if self.remove_error is not None:
            raise self.remove_error
        self.remove_calls.append((bucket_name, object_name))

    def presigned_get_object(self, bucket_name: str, object_name: str, expires) -> str:
        if self.presigned_error is not None:
            raise self.presigned_error
        self.presigned_calls.append((bucket_name, object_name, expires))
        return f"http://localhost:9000/{bucket_name}/{object_name}?signature=test"


def _build_service(client: FakeMinioClient) -> MinioStorageService:
    return MinioStorageService(
        endpoint="localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin",
        bucket="package-images",
        secure=False,
        client=client,
    )


def test_upload_image_succeeds() -> None:
    client = FakeMinioClient()
    storage = _build_service(client)

    stored_object = storage.upload_image(
        "packages/cape-town-tour/photo.jpg",
        b"\xff\xd8\xfftest",
        "image/jpeg",
    )

    assert client.put_calls == [
        ("package-images", "packages/cape-town-tour/photo.jpg", b"\xff\xd8\xfftest", 7, "image/jpeg")
    ]
    assert stored_object.url == "http://localhost:9000/package-images/packages/cape-town-tour/photo.jpg"


def test_delete_image_succeeds() -> None:
    client = FakeMinioClient()
    storage = _build_service(client)

    storage.delete_image("packages/cape-town-tour/photo.jpg")

    assert client.remove_calls == [("package-images", "packages/cape-town-tour/photo.jpg")]


def test_invalid_credentials_fail_gracefully() -> None:
    client = FakeMinioClient(bucket_exists_error=_s3_error("InvalidAccessKeyId"))
    storage = _build_service(client)

    with pytest.raises(StorageAuthenticationError):
        storage.upload_image("packages/cape-town-tour/photo.jpg", b"\xff\xd8\xfftest", "image/jpeg")


def test_missing_bucket_returns_specific_error() -> None:
    client = FakeMinioClient(bucket_exists_result=False)
    storage = _build_service(client)

    with pytest.raises(StorageBucketNotFoundError):
        storage.upload_image("packages/cape-town-tour/photo.jpg", b"\x89PNG\r\n\x1a\ntest", "image/png")


def test_get_presigned_url_succeeds() -> None:
    client = FakeMinioClient()
    storage = _build_service(client)

    url = storage.get_presigned_url("packages/cape-town-tour/photo.jpg", hours=2)

    assert url == (
        "http://localhost:9000/package-images/packages/cape-town-tour/photo.jpg?signature=test"
    )
    assert client.presigned_calls
