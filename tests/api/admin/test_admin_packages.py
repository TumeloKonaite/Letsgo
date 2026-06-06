from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fastapi.testclient import TestClient
import pytest

from app.core.config import Settings
from app.infrastructure.database.models import Package, PackagePublicationStatus
from app.main import create_application
from tests.api.test_admin_auth import (
    TEST_ADMIN_ROLE,
    TEST_AUDIENCE,
    TEST_ISSUER,
    TEST_JWKS_URL,
    _build_auth_service,
    _build_token,
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
    database_url = f"sqlite:///{tmp_path / 'admin-packages.db'}"
    application = create_application(
        settings=Settings(
            database_url=database_url,
            keycloak_issuer=TEST_ISSUER,
            keycloak_audience=TEST_AUDIENCE,
            keycloak_jwks_url=TEST_JWKS_URL,
            keycloak_admin_role=TEST_ADMIN_ROLE,
        )
    )

    with TestClient(application) as client:
        application.state.keycloak_auth_service = _build_auth_service()
        package_id = _seed_package(application.state.db_session_factory)
        yield AdminPackagesClient(client=client, package_id=package_id)


def _admin_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_build_token(roles=['admin'])}"}


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
            "is_active": True,
            "status": "draft",
            "is_published": False,
            "is_featured": True,
            "display_order": 3,
        },
    )

    assert response.status_code == 201
    assert response.json()["slug"] == "garden-route-escape"


def test_create_package_duplicate_slug_fails(admin_packages_client: AdminPackagesClient) -> None:
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
        },
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Updated Existing Package"
    assert response.json()["destination"] == "Johannesburg"
    assert response.json()["price_from"] == "4999.00"


def test_update_missing_package_fails(admin_packages_client: AdminPackagesClient) -> None:
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


def test_delete_missing_package_fails(admin_packages_client: AdminPackagesClient) -> None:
    response = admin_packages_client.client.delete(
        "/api/admin/packages/999999",
        headers=_admin_headers(),
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Package not found"}


def test_admin_endpoints_require_authentication(admin_packages_client: AdminPackagesClient) -> None:
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


def test_admin_endpoints_require_admin_role(admin_packages_client: AdminPackagesClient) -> None:
    response = admin_packages_client.client.patch(
        f"/api/admin/packages/{admin_packages_client.package_id}/publish",
        headers={"Authorization": f"Bearer {_build_token(roles=['editor'])}"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Admin role required"}
