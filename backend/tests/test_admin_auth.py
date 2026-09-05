from __future__ import annotations

from decimal import Decimal

import pytest
from app.api.routes.admin.auth import router as admin_auth_router
from app.api.routes.admin.packages import router as admin_packages_router
from app.api.routes.packages.public import router as public_packages_router
from app.auth.clerk_auth import ClerkTokenValidationError
from app.core.config import Settings
from app.domain.auth.models import AuthenticatedUser
from app.domain.packages.repository import PackageRecord
from app.domain.packages.service import PackageService
from app.infrastructure.database.models import PackagePublicationStatus
from app.infrastructure.packages.in_memory_package_repository import (
    InMemoryPackageRepository,
)
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient


class StubClerkAuthService:
    def __init__(self) -> None:
        self._tokens: dict[str, AuthenticatedUser] = {}

    def add_token(self, token: str, user: AuthenticatedUser) -> None:
        self._tokens[token] = user

    def verify_token(self, token: str) -> AuthenticatedUser:
        try:
            return self._tokens[token]
        except KeyError as exc:
            raise ClerkTokenValidationError("Invalid token") from exc


@pytest.fixture
def client() -> TestClient:
    repository = InMemoryPackageRepository(
        packages=[
            PackageRecord(
                id=1,
                title="Safari",
                slug="safari",
                short_description="Open listing",
                description="Published safari package",
                destination="Kruger",
                duration_days=3,
                duration_nights=2,
                price_from=Decimal("499.00"),
                currency="ZAR",
                is_active=True,
                status=PackagePublicationStatus.PUBLISHED,
                is_published=True,
                is_featured=False,
                display_order=0,
            )
        ]
    )
    app = FastAPI()
    api_router = APIRouter(prefix="/api")
    api_router.include_router(public_packages_router)
    api_router.include_router(admin_auth_router)
    api_router.include_router(admin_packages_router)
    app.include_router(api_router)
    app.state.settings = Settings(
        environment="test",
        api_prefix="/api",
        database_url="sqlite:///./test.db",
        clerk_admin_claim="admin",
    )
    app.state.package_service = PackageService(repository=repository)
    app.state.authentication_provider = StubClerkAuthService()
    return TestClient(app)


def _package_payload(*, slug: str = "garden-route") -> dict[str, object]:
    return {
        "title": "Garden Route Escape",
        "slug": slug,
        "short_description": "Coastal tour",
        "description": "A longer scenic route package",
        "destination": "Garden Route",
        "duration_days": 5,
        "duration_nights": 4,
        "price_from": "1299.00",
        "currency": "ZAR",
        "is_active": True,
        "status": "draft",
        "is_published": False,
        "is_featured": False,
        "display_order": 2,
    }


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_public_packages_endpoint_stays_open(client: TestClient) -> None:
    response = client.get("/api/packages")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "slug": "safari",
            "title": "Safari",
            "short_description": "Open listing",
            "location": "Kruger",
            "duration_days": 3,
            "price_from": "499.00",
            "currency": "ZAR",
            "hero_image_url": None,
            "is_featured": False,
        }
    ]


def test_admin_endpoint_returns_401_without_token(client: TestClient) -> None:
    response = client.get("/api/admin/packages")

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing credentials"}


def test_admin_endpoint_returns_401_for_invalid_token(client: TestClient) -> None:
    response = client.get("/api/admin/packages", headers=_auth_headers("invalid-token"))

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing credentials"}


def test_admin_endpoint_returns_403_for_non_admin_user(client: TestClient) -> None:
    client.app.state.authentication_provider.add_token(
        "member-token",
        AuthenticatedUser(
            subject="user-123",
            email="member@example.com",
            provider="clerk",
        ),
    )

    response = client.get("/api/admin/packages", headers=_auth_headers("member-token"))

    assert response.status_code == 403
    assert response.json() == {"detail": "Admin role required"}


def test_admin_user_can_manage_packages(client: TestClient) -> None:
    client.app.state.authentication_provider.add_token(
        "admin-token",
        AuthenticatedUser(
            subject="admin-123",
            email="admin@example.com",
            provider="clerk",
            roles=frozenset({"admin"}),
        ),
    )

    create_response = client.post(
        "/api/admin/packages",
        headers=_auth_headers("admin-token"),
        json=_package_payload(),
    )
    assert create_response.status_code == 201
    package_id = create_response.json()["id"]

    update_response = client.patch(
        f"/api/admin/packages/{package_id}",
        headers=_auth_headers("admin-token"),
        json={"title": "Updated Garden Route Escape"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Updated Garden Route Escape"

    publish_response = client.patch(
        f"/api/admin/packages/{package_id}/publish",
        headers=_auth_headers("admin-token"),
    )
    assert publish_response.status_code == 200
    assert publish_response.json()["is_published"] is True
    assert publish_response.json()["status"] == "published"

    public_response = client.get("/api/packages/garden-route")
    assert public_response.status_code == 200
    assert public_response.json()["slug"] == "garden-route"

    unpublish_response = client.patch(
        f"/api/admin/packages/{package_id}/unpublish",
        headers=_auth_headers("admin-token"),
    )
    assert unpublish_response.status_code == 200
    assert unpublish_response.json()["is_published"] is False
    assert unpublish_response.json()["status"] == "draft"

    delete_response = client.delete(
        f"/api/admin/packages/{package_id}",
        headers=_auth_headers("admin-token"),
    )
    assert delete_response.status_code == 204

    deleted_response = client.get(
        f"/api/admin/packages/{package_id}",
        headers=_auth_headers("admin-token"),
    )
    assert deleted_response.status_code == 404
