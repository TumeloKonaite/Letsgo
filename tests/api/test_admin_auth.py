from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import pytest
from app.infrastructure.database.models import Package, PackageImage
from app.main import create_application
from fastapi.testclient import TestClient

from tests.api.firebase_auth_helpers import (
    TEST_ADMIN_TOKEN,
    TEST_EDITOR_TOKEN,
    TEST_EXPIRED_TOKEN,
    bearer_headers,
    build_test_settings,
    install_stub_firebase_auth,
)


@dataclass(frozen=True, slots=True)
class SeededAdminClient:
    client: TestClient
    package_id: int
    image_id: int


def _seed_existing_package(session_factory) -> tuple[int, int]:
    with session_factory() as session:
        package = Package(
            title="Test Package",
            slug="test-package",
            short_description="Existing package.",
            description="Existing package for admin tests.",
            destination="Cape Town",
            duration_days=3,
            duration_nights=2,
            price_from=Decimal("1999.00"),
            currency="ZAR",
        )
        package.images.append(
            PackageImage(
                image_url="https://example.com/existing.jpg",
                alt_text="Existing image",
                sort_order=0,
                is_cover=True,
            )
        )
        session.add(package)
        session.commit()
        session.refresh(package)
        return package.id, package.images[0].id


@pytest.fixture
def admin_client(tmp_path) -> SeededAdminClient:
    database_url = f"sqlite:///{tmp_path / 'admin.db'}"
    application = create_application(settings=build_test_settings(database_url))

    with TestClient(application) as client:
        install_stub_firebase_auth(application)
        package_id, image_id = _seed_existing_package(
            application.state.db_session_factory
        )
        yield SeededAdminClient(client=client, package_id=package_id, image_id=image_id)


def test_valid_firebase_token_is_accepted(admin_client: SeededAdminClient) -> None:
    response = admin_client.client.get(
        "/api/admin/auth/me",
        headers=bearer_headers(TEST_ADMIN_TOKEN),
    )

    assert response.status_code == 200
    assert response.json() == {
        "sub": "admin-user-1",
        "username": "admin.user",
        "email": "admin@example.com",
        "claims": {"admin": True},
    }


@pytest.mark.parametrize(
    ("method", "path", "payload", "files", "form_data"),
    [
        ("GET", "/api/admin/packages/{package_id}", None, None, None),
        (
            "POST",
            "/api/admin/packages",
            {
                "title": "New Package",
                "slug": "new-package",
                "short_description": "Short description",
                "description": "Long description",
                "destination": "Johannesburg",
                "duration_days": 5,
                "duration_nights": 4,
                "price_from": "5999.00",
                "currency": "ZAR",
                "is_active": True,
                "status": "draft",
                "is_published": False,
                "is_featured": False,
                "display_order": 1,
            },
            None,
            None,
        ),
        (
            "PUT",
            "/api/admin/packages/{package_id}",
            {
                "title": "Updated Package",
                "slug": "updated-package",
                "short_description": "Short description",
                "description": "Long description",
                "destination": "Pretoria",
                "duration_days": 4,
                "duration_nights": 3,
                "price_from": "7999.00",
                "currency": "ZAR",
                "is_active": True,
                "status": "published",
                "is_published": True,
                "is_featured": True,
                "display_order": 2,
            },
            None,
            None,
        ),
        (
            "PATCH",
            "/api/admin/packages/{package_id}",
            {"title": "Patched Package"},
            None,
            None,
        ),
        ("DELETE", "/api/admin/packages/{package_id}", None, None, None),
        (
            "POST",
            "/api/admin/packages/{package_id}/images",
            None,
            {"file": ("new-image.jpg", b"\xff\xd8\xfftest", "image/jpeg")},
            {"alt_text": "New image", "display_order": "1"},
        ),
        (
            "DELETE",
            "/api/admin/packages/{package_id}/images/{image_id}",
            None,
            None,
            None,
        ),
    ],
)
def test_missing_token_returns_401_for_all_admin_package_mutations(
    admin_client: SeededAdminClient,
    method: str,
    path: str,
    payload: dict[str, object] | None,
    files,
    form_data,
) -> None:
    response = admin_client.client.request(
        method,
        path.format(package_id=admin_client.package_id, image_id=admin_client.image_id),
        json=payload,
        files=files,
        data=form_data,
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Missing bearer token"}


def test_invalid_token_returns_401(admin_client: SeededAdminClient) -> None:
    response = admin_client.client.post(
        "/api/admin/packages",
        headers=bearer_headers("invalid-token"),
        json={
            "title": "New Package",
            "slug": "new-package",
            "short_description": "Short description",
            "description": "Long description",
            "destination": "Johannesburg",
            "duration_days": 5,
            "duration_nights": 4,
            "price_from": "5999.00",
            "currency": "ZAR",
            "is_active": True,
            "status": "draft",
            "is_published": False,
            "is_featured": False,
            "display_order": 1,
        },
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token"}


def test_expired_token_returns_401(admin_client: SeededAdminClient) -> None:
    response = admin_client.client.post(
        "/api/admin/packages",
        headers=bearer_headers(TEST_EXPIRED_TOKEN),
        json={
            "title": "New Package",
            "slug": "new-package",
            "short_description": "Short description",
            "description": "Long description",
            "destination": "Johannesburg",
            "duration_days": 5,
            "duration_nights": 4,
            "price_from": "5999.00",
            "currency": "ZAR",
            "is_active": True,
            "status": "draft",
            "is_published": False,
            "is_featured": False,
            "display_order": 1,
        },
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Token expired"}


def test_user_with_admin_claim_can_access_protected_routes(
    admin_client: SeededAdminClient,
) -> None:
    response = admin_client.client.post(
        "/api/admin/packages",
        headers=bearer_headers(TEST_ADMIN_TOKEN),
        json={
            "title": "New Package",
            "slug": "new-package",
            "short_description": "Short description",
            "description": "Long description",
            "destination": "Johannesburg",
            "duration_days": 5,
            "duration_nights": 4,
            "price_from": "5999.00",
            "currency": "ZAR",
            "is_active": True,
            "status": "draft",
            "is_published": False,
            "is_featured": False,
            "display_order": 1,
        },
    )

    assert response.status_code == 201
    assert response.json()["slug"] == "new-package"


def test_user_without_admin_claim_receives_403(admin_client: SeededAdminClient) -> None:
    response = admin_client.client.patch(
        f"/api/admin/packages/{admin_client.package_id}",
        headers=bearer_headers(TEST_EDITOR_TOKEN),
        json={"title": "Forbidden Update"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Admin claim required"}


def test_application_fails_fast_when_firebase_configuration_is_missing(
    tmp_path,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'missing-firebase.db'}"

    with pytest.raises(
        ValueError,
        match="Missing required Firebase configuration: FIREBASE_PROJECT_ID",
    ):
        create_application(
            settings=build_test_settings(database_url, firebase_project_id=None)
        )
