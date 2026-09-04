from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import uuid4

import pytest
from app.infrastructure.database.models import Package, PackagePublicationStatus
from app.main import create_application
from fastapi.testclient import TestClient

from tests.api.firebase_auth_helpers import (
    TEST_ADMIN_TOKEN,
    TEST_EDITOR_TOKEN,
    bearer_headers,
    build_test_settings,
    install_stub_firebase_auth,
)


@dataclass(frozen=True, slots=True)
class AdminPackagesClient:
    client: TestClient
    package_id: int


def _seed_package(session_factory) -> int:
    with session_factory() as session:
        package = Package(
            title="Existing Package",
            slug="existing-package",
            short_description="Existing package.",
            description="Existing package for admin CRUD tests.",
            destination="Cape Town",
            duration_days=4,
            duration_nights=3,
            price_from=Decimal("4500.00"),
            currency="ZAR",
            status=PackagePublicationStatus.DRAFT,
            is_published=False,
        )
        session.add(package)
        session.commit()
        session.refresh(package)
        return package.id


@pytest.fixture
def admin_packages_client(tmp_path) -> AdminPackagesClient:
    database_path = tmp_path / f"admin-packages-{uuid4().hex}.db"
    database_url = f"sqlite:///{database_path}"
    application = create_application(settings=build_test_settings(database_url))

    with TestClient(application) as client:
        install_stub_firebase_auth(application)
        package_id = _seed_package(application.state.db_session_factory)
        yield AdminPackagesClient(client=client, package_id=package_id)


def _admin_headers() -> dict[str, str]:
    return bearer_headers(TEST_ADMIN_TOKEN)


def test_create_package_success(admin_packages_client: AdminPackagesClient) -> None:
    response = admin_packages_client.client.post(
        "/api/admin/packages",
        headers=_admin_headers(),
        json={
            "title": "Garden Route Escape",
            "slug": "garden-route-escape",
            "short_description": "Scenic coastline road trip.",
            "description": "A guided route through the Garden Route highlights.",
            "destination": "Garden Route",
            "duration_days": 5,
            "duration_nights": 4,
            "price_from": "6200.00",
            "currency": "ZAR",
            "itinerary": [
                {
                    "title": "Knysna Waterfront",
                    "description": "Start with the lagoon and waterfront.",
                    "duration": "45 minutes",
                    "display_order": 0,
                }
            ],
            "inclusions": [
                {
                    "name": "Bottled water",
                    "type": "included",
                    "display_order": 0,
                },
                {
                    "name": "Lunch",
                    "type": "excluded",
                    "display_order": 0,
                },
            ],
            "is_active": True,
            "status": "draft",
            "is_published": False,
            "is_featured": True,
            "display_order": 3,
        },
    )

    assert response.status_code == 201
    assert response.json()["slug"] == "garden-route-escape"
    assert response.json()["itinerary"][0]["title"] == "Knysna Waterfront"
    assert response.json()["inclusions"][0]["name"] == "Lunch"


def test_create_package_duplicate_slug_fails(
    admin_packages_client: AdminPackagesClient,
) -> None:
    response = admin_packages_client.client.post(
        "/api/admin/packages",
        headers=_admin_headers(),
        json={
            "title": "Duplicate Package",
            "slug": "existing-package",
            "short_description": "Duplicate.",
            "description": "Duplicate slug should fail.",
            "destination": "Johannesburg",
            "duration_days": 2,
            "duration_nights": 1,
            "price_from": "2100.00",
            "currency": "ZAR",
            "is_active": True,
            "status": "draft",
            "is_published": False,
            "is_featured": False,
            "display_order": 0,
        },
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Package slug already exists"}


def test_get_package_success(admin_packages_client: AdminPackagesClient) -> None:
    response = admin_packages_client.client.get(
        f"/api/admin/packages/{admin_packages_client.package_id}",
        headers=_admin_headers(),
    )

    assert response.status_code == 200
    assert response.json()["id"] == admin_packages_client.package_id
    assert response.json()["slug"] == "existing-package"
    assert response.json()["itinerary"] == []
    assert response.json()["inclusions"] == []


def test_get_missing_package_fails(admin_packages_client: AdminPackagesClient) -> None:
    response = admin_packages_client.client.get(
        "/api/admin/packages/999999",
        headers=_admin_headers(),
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Package not found"}


def test_update_package_success(admin_packages_client: AdminPackagesClient) -> None:
    response = admin_packages_client.client.patch(
        f"/api/admin/packages/{admin_packages_client.package_id}",
        headers=_admin_headers(),
        json={
            "title": "Updated Existing Package",
            "destination": "Johannesburg",
            "price_from": "4999.00",
            "itinerary": [
                {
                    "title": "Vilakazi Street",
                    "description": "Walk the historic street.",
                    "duration": "30 minutes",
                    "display_order": 0,
                }
            ],
            "inclusions": [
                {
                    "name": "Guide",
                    "type": "included",
                    "display_order": 0,
                }
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Updated Existing Package"
    assert response.json()["destination"] == "Johannesburg"
    assert response.json()["price_from"] == "4999.00"
    assert response.json()["itinerary"][0]["duration"] == "30 minutes"
    assert response.json()["inclusions"][0]["name"] == "Guide"


def test_update_missing_package_fails(
    admin_packages_client: AdminPackagesClient,
) -> None:
    response = admin_packages_client.client.patch(
        "/api/admin/packages/999999",
        headers=_admin_headers(),
        json={"title": "Missing"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Package not found"}


def test_publish_package_success(admin_packages_client: AdminPackagesClient) -> None:
    response = admin_packages_client.client.patch(
        f"/api/admin/packages/{admin_packages_client.package_id}/publish",
        headers=_admin_headers(),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "published"
    assert response.json()["is_published"] is True


def test_unpublish_package_success(admin_packages_client: AdminPackagesClient) -> None:
    admin_packages_client.client.patch(
        f"/api/admin/packages/{admin_packages_client.package_id}/publish",
        headers=_admin_headers(),
    )

    response = admin_packages_client.client.patch(
        f"/api/admin/packages/{admin_packages_client.package_id}/unpublish",
        headers=_admin_headers(),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "draft"
    assert response.json()["is_published"] is False


def test_delete_package_success(admin_packages_client: AdminPackagesClient) -> None:
    response = admin_packages_client.client.delete(
        f"/api/admin/packages/{admin_packages_client.package_id}",
        headers=_admin_headers(),
    )

    assert response.status_code == 204


def test_delete_missing_package_fails(
    admin_packages_client: AdminPackagesClient,
) -> None:
    response = admin_packages_client.client.delete(
        "/api/admin/packages/999999",
        headers=_admin_headers(),
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Package not found"}


def test_admin_endpoints_require_authentication(
    admin_packages_client: AdminPackagesClient,
) -> None:
    response = admin_packages_client.client.post(
        "/api/admin/packages",
        json={
            "title": "Unauthenticated Package",
            "slug": "unauthenticated-package",
            "short_description": "Should fail.",
            "description": "Missing token should be rejected.",
            "destination": "Durban",
            "duration_days": 3,
            "duration_nights": 2,
            "price_from": "3200.00",
            "currency": "ZAR",
            "is_active": True,
            "status": "draft",
            "is_published": False,
            "is_featured": False,
            "display_order": 0,
        },
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Missing bearer token"}


def test_admin_endpoints_require_admin_claim(
    admin_packages_client: AdminPackagesClient,
) -> None:
    response = admin_packages_client.client.patch(
        f"/api/admin/packages/{admin_packages_client.package_id}/publish",
        headers=bearer_headers(TEST_EDITOR_TOKEN),
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Admin claim required"}
