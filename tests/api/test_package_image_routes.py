from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from fastapi.testclient import TestClient
import pytest

from app.domain.packages.storage import StoredObject
from app.infrastructure.database.models import Package, PackageImage
from app.main import create_application
from tests.api.firebase_auth_helpers import (
    TEST_ADMIN_TOKEN,
    TEST_EDITOR_TOKEN,
    bearer_headers,
    build_test_settings,
    install_stub_firebase_auth,
)


@dataclass(slots=True)
class FakeStorageService:
    uploads: dict[str, bytes] = field(default_factory=dict)
    deleted: list[str] = field(default_factory=list)

    def upload_image(self, object_name: str, content: bytes, content_type: str) -> StoredObject:
        self.uploads[object_name] = content
        return StoredObject(
            object_name=object_name,
            url=self.get_public_url(object_name),
            content_type=content_type,
            size=len(content),
        )

    def delete_image(self, object_name: str) -> None:
        self.deleted.append(object_name)
        self.uploads.pop(object_name, None)

    def get_public_url(self, object_name: str) -> str:
        return f"https://storage.googleapis.com/letsgosa-package-images/{object_name}"

    def extract_object_name(self, url: str) -> str | None:
        prefix = "https://storage.googleapis.com/letsgosa-package-images/"
        if not url.startswith(prefix):
            return None
        return url[len(prefix) :].split("?", 1)[0]


@dataclass(frozen=True, slots=True)
class PackageImagesClient:
    client: TestClient
    package_id: int
    storage: FakeStorageService
    session_factory: object


def _seed_package(session_factory) -> int:
    with session_factory() as session:
        package = Package(
            title="Cape Town Explorer",
            slug="cape-town-explorer",
            short_description="Coastal highlights.",
            description="A package used for image upload tests.",
            destination="Cape Town",
            duration_days=4,
            duration_nights=3,
            price_from=Decimal("4999.00"),
            currency="ZAR",
        )
        session.add(package)
        session.commit()
        session.refresh(package)
        return package.id


@pytest.fixture
def package_images_client(tmp_path) -> PackageImagesClient:
    database_url = f"sqlite:///{tmp_path / 'package-images.db'}"
    application = create_application(
        settings=build_test_settings(
            database_url,
            package_image_max_upload_bytes=128,
        )
    )
    storage = FakeStorageService()

    with TestClient(application) as client:
        install_stub_firebase_auth(application)
        application.state.storage_service = storage
        package_id = _seed_package(application.state.db_session_factory)
        yield PackageImagesClient(
            client=client,
            package_id=package_id,
            storage=storage,
            session_factory=application.state.db_session_factory,
        )


def _admin_headers() -> dict[str, str]:
    return bearer_headers(TEST_ADMIN_TOKEN)


def _jpeg_bytes() -> bytes:
    return b"\xff\xd8\xff\xe0" + b"jpeg-data"


def test_authenticated_admin_can_upload_images(package_images_client: PackageImagesClient) -> None:
    response = package_images_client.client.post(
        f"/api/admin/packages/{package_images_client.package_id}/images",
        headers=_admin_headers(),
        files={"file": ("cape-town.jpg", _jpeg_bytes(), "image/jpeg")},
        data={"alt_text": "Table Mountain view", "display_order": "1", "is_cover": "true"},
    )

    assert response.status_code == 201
    payload = response.json()

    assert payload["package_id"] == package_images_client.package_id
    assert payload["alt_text"] == "Table Mountain view"
    assert payload["display_order"] == 1
    assert payload["is_cover"] is True
    assert payload["url"].startswith(
        "https://storage.googleapis.com/letsgosa-package-images/packages/cape-town-explorer/"
    )
    assert len(package_images_client.storage.uploads) == 1


def test_non_admin_users_receive_403(package_images_client: PackageImagesClient) -> None:
    response = package_images_client.client.post(
        f"/api/admin/packages/{package_images_client.package_id}/images",
        headers=bearer_headers(TEST_EDITOR_TOKEN),
        files={"file": ("cape-town.jpg", _jpeg_bytes(), "image/jpeg")},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Admin claim required"}


def test_unsupported_file_types_receive_400(package_images_client: PackageImagesClient) -> None:
    response = package_images_client.client.post(
        f"/api/admin/packages/{package_images_client.package_id}/images",
        headers=_admin_headers(),
        files={"file": ("notes.txt", b"plain-text", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Unsupported image format. Supported formats: JPEG, PNG, WebP."
    }


def test_oversized_files_receive_400(package_images_client: PackageImagesClient) -> None:
    response = package_images_client.client.post(
        f"/api/admin/packages/{package_images_client.package_id}/images",
        headers=_admin_headers(),
        files={"file": ("cape-town.png", b"\x89PNG\r\n\x1a\n" + (b"x" * 256), "image/png")},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Image exceeds maximum upload size of 128 bytes."}


def test_uploaded_image_metadata_is_persisted_and_listed(
    package_images_client: PackageImagesClient,
) -> None:
    upload_response = package_images_client.client.post(
        f"/api/admin/packages/{package_images_client.package_id}/images",
        headers=_admin_headers(),
        files={"file": ("cape-town.webp", b"RIFF\x00\x00\x00\x00WEBPpayload", "image/webp")},
        data={"alt_text": "Coastline", "display_order": "3"},
    )
    assert upload_response.status_code == 201

    image_id = upload_response.json()["id"]

    list_response = package_images_client.client.get(
        f"/api/admin/packages/{package_images_client.package_id}/images",
        headers=_admin_headers(),
    )

    assert list_response.status_code == 200
    assert list_response.json() == [
        {
            "id": image_id,
            "package_id": package_images_client.package_id,
            "url": upload_response.json()["url"],
            "alt_text": "Coastline",
            "display_order": 3,
            "is_cover": False,
        }
    ]

    with package_images_client.session_factory() as session:
        image = session.get(PackageImage, image_id)

    assert image is not None
    assert image.package_id == package_images_client.package_id
    assert image.alt_text == "Coastline"
    assert image.sort_order == 3
    assert image.storage_key is not None
    assert image.image_url.startswith(
        "https://storage.googleapis.com/letsgosa-package-images/packages/cape-town-explorer/"
    )


def test_images_can_be_deleted(package_images_client: PackageImagesClient) -> None:
    upload_response = package_images_client.client.post(
        f"/api/admin/packages/{package_images_client.package_id}/images",
        headers=_admin_headers(),
        files={"file": ("cape-town.jpg", _jpeg_bytes(), "image/jpeg")},
    )
    image_id = upload_response.json()["id"]

    delete_response = package_images_client.client.delete(
        f"/api/admin/packages/{package_images_client.package_id}/images/{image_id}",
        headers=_admin_headers(),
    )

    assert delete_response.status_code == 204
    assert len(package_images_client.storage.deleted) == 1

    with package_images_client.session_factory() as session:
        assert session.get(PackageImage, image_id) is None
