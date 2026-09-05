from __future__ import annotations

from dataclasses import dataclass, field

import pytest
from app.domain.packages.storage import (
    StorageAuthenticationError,
    StorageBucketNotFoundError,
    StorageError,
)
from app.infrastructure.storage.gcs_storage import GcsStorageService
from google.api_core.exceptions import Forbidden, NotFound


@dataclass
class FakeBlob:
    object_name: str
    uploads: list[tuple[str, bytes, int, str]] = field(default_factory=list)
    upload_error: Exception | None = None
    delete_error: Exception | None = None
    deleted: bool = False

    def upload_from_string(self, content, *, content_type, if_generation_match):
        assert if_generation_match == 0
        if self.upload_error:
            raise self.upload_error
        self.uploads.append((self.object_name, content, len(content), content_type))

    def generate_signed_url(self, **kwargs):
        assert kwargs["method"] == "GET"
        return (
            "https://storage.googleapis.com/letsgosa-package-images/"
            + self.object_name
            + "?signature=synthetic"
        )

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
        project_id="test-project",
        bucket_name="letsgosa-package-images",
        object_prefix="staging/",
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

    assert bucket.blobs["staging/packages/cape-town-tour/photo.jpg"].uploads == [
        (
            "staging/packages/cape-town-tour/photo.jpg",
            b"\xff\xd8\xfftest",
            7,
            "image/jpeg",
        )
    ]
    assert stored_object.url == (
        "https://storage.googleapis.com/letsgosa-package-images/staging/packages/cape-town-tour/photo.jpg"
    )


def test_delete_image_succeeds() -> None:
    bucket = FakeBucket(name="letsgosa-package-images")
    storage = _build_service(bucket)

    storage.delete_image("staging/packages/cape-town-tour/photo.jpg")

    assert bucket.blobs["staging/packages/cape-town-tour/photo.jpg"].deleted is True


def test_invalid_credentials_fail_gracefully() -> None:
    bucket = FakeBucket(
        name="letsgosa-package-images", blob_upload_error=Forbidden("denied")
    )
    storage = _build_service(bucket)

    with pytest.raises(StorageAuthenticationError):
        storage.upload_image(
            "packages/cape-town-tour/photo.jpg",
            b"\xff\xd8\xfftest",
            "image/jpeg",
        )


def test_missing_bucket_returns_specific_error() -> None:
    bucket = FakeBucket(
        name="letsgosa-package-images", blob_upload_error=NotFound("missing")
    )
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
            "https://storage.googleapis.com/letsgosa-package-images/staging/packages/cape-town-tour/photo.jpg?signature=synthetic"
        )
        == "staging/packages/cape-town-tour/photo.jpg"
    )


def test_network_errors_are_wrapped_as_storage_errors() -> None:
    bucket = FakeBucket(
        name="letsgosa-package-images", blob_upload_error=OSError("connection refused")
    )
    storage = _build_service(bucket)

    with pytest.raises(StorageError, match="Image storage unavailable"):
        storage.upload_image(
            "staging/packages/cape-town-tour/photo.jpg", b"data", "image/jpeg"
        )


def test_missing_object_delete_is_ignored() -> None:
    bucket = FakeBucket(
        name="letsgosa-package-images", blob_delete_error=NotFound("missing")
    )
    storage = _build_service(bucket)

    storage.delete_image("staging/packages/cape-town-tour/photo.jpg")


@pytest.mark.parametrize("name", ["other/x.jpg", "staging/../x.jpg", "staging//x.jpg"])
def test_rejects_outside_prefix(name):
    storage = _build_service(FakeBucket(name="letsgosa-package-images"))
    with pytest.raises(StorageError):
        storage.delete_image(name)
    with pytest.raises(StorageError):
        storage.get_public_url(name)


def test_client_auth_error_is_sanitized():
    from google.auth.exceptions import RefreshError

    def fail():
        raise RefreshError("sensitive provider response")

    storage = GcsStorageService(
        project_id="test",
        bucket_name="test-bucket",
        object_prefix="staging/",
        client_factory=fail,
    )
    with pytest.raises(
        StorageAuthenticationError, match="^Image storage unavailable$"
    ) as error:
        storage.delete_image("staging/x.jpg")
    assert error.value.__suppress_context__


def test_private_url_is_signed_on_read():
    storage = _build_service(FakeBucket(name="letsgosa-package-images"))
    assert "?signature=" in storage.get_public_url("staging/packages/x.jpg")


def test_modal_supplier_does_not_fall_back(monkeypatch):
    from app.infrastructure.storage.gcs_storage import ModalTokenSupplier
    from google.auth.exceptions import GoogleAuthError

    monkeypatch.delenv("MODAL_IDENTITY_TOKEN", raising=False)
    with pytest.raises(GoogleAuthError):
        ModalTokenSupplier().get_subject_token(None, None)
    monkeypatch.setenv("MODAL_IDENTITY_TOKEN", "synthetic")
    assert ModalTokenSupplier().get_subject_token(None, None) == "synthetic"


def test_factory_uses_explicit_federation(monkeypatch):
    from app.core.config import Settings
    from app.infrastructure.storage import gcs_storage

    captured = {}

    def credentials(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(gcs_storage.identity_pool, "Credentials", credentials)
    bucket = FakeBucket(name="letsgosa-package-images")
    monkeypatch.setattr(gcs_storage, "Client", lambda **kwargs: FakeGcsClient(bucket))
    settings = Settings(
        environment="staging",
        storage_provider="gcs",
        gcp_project_id="test-project",
        gcs_bucket_name=bucket.name,
        gcs_object_prefix="staging/",
        gcs_wif_audience="//iam.googleapis.com/projects/123/locations/global/workloadIdentityPools/modal/providers/staging",
        gcs_service_account_email="modal-staging@test-project.iam.gserviceaccount.com",
    )
    storage = gcs_storage.create_storage_service(settings)
    storage.upload_image("packages/x.jpg", b"data", "image/jpeg")
    assert captured["audience"] == settings.gcs_wif_audience
    assert isinstance(
        captured["subject_token_supplier"], gcs_storage.ModalTokenSupplier
    )
    assert captured["service_account_impersonation_url"].endswith(
        settings.gcs_service_account_email + ":generateAccessToken"
    )
