from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import pytest
from app.infrastructure.database.models import Booking, BookingStatus, Package
from app.main import create_application
from fastapi.testclient import TestClient

from tests.api.clerk_auth_helpers import (
    TEST_ADMIN_TOKEN,
    TEST_EDITOR_TOKEN,
    bearer_headers,
    build_test_settings,
    install_stub_clerk_auth,
)


@dataclass(frozen=True, slots=True)
class AdminBookingsClient:
    client: TestClient
    package_id: int
    booking_id: int
    contacted_booking_id: int


def _seed_bookings(session_factory) -> tuple[int, int, int]:
    with session_factory() as session:
        package = Package(
            title="Safari Adventure",
            slug="safari-adventure",
            short_description="A guided safari.",
            description="Multi-day safari with transport and accommodation.",
            destination="Kruger",
            duration_days=4,
            duration_nights=3,
            price_from=Decimal("8999.00"),
            currency="ZAR",
        )
        session.add(package)
        session.flush()

        new_booking = Booking(
            package_id=package.id,
            customer_name="Alex New",
            customer_email="alex.new@example.com",
            customer_phone="+27 82 111 1111",
            number_of_people=2,
            special_requests="Window seat if possible",
            status=BookingStatus.NEW,
        )
        contacted_booking = Booking(
            package_id=package.id,
            customer_name="Casey Contacted",
            customer_email="casey.contacted@example.com",
            customer_phone="+27 82 222 2222",
            number_of_people=4,
            special_requests=None,
            status=BookingStatus.CONTACTED,
        )
        session.add_all([new_booking, contacted_booking])
        session.commit()
        session.refresh(new_booking)
        session.refresh(contacted_booking)
        return package.id, new_booking.id, contacted_booking.id


@pytest.fixture
def admin_bookings_client(tmp_path) -> AdminBookingsClient:
    database_url = f"sqlite:///{tmp_path / 'admin-bookings.db'}"
    application = create_application(settings=build_test_settings(database_url))

    with TestClient(application) as client:
        install_stub_clerk_auth(application)
        package_id, booking_id, contacted_booking_id = _seed_bookings(
            application.state.db_session_factory
        )
        yield AdminBookingsClient(
            client=client,
            package_id=package_id,
            booking_id=booking_id,
            contacted_booking_id=contacted_booking_id,
        )


def _admin_headers() -> dict[str, str]:
    return bearer_headers(TEST_ADMIN_TOKEN)


def test_missing_token_returns_401(admin_bookings_client: AdminBookingsClient) -> None:
    response = admin_bookings_client.client.get("/api/admin/bookings")

    assert response.status_code == 401
    assert response.json() == {"detail": "Missing bearer token"}


def test_non_admin_token_returns_403(
    admin_bookings_client: AdminBookingsClient,
) -> None:
    response = admin_bookings_client.client.get(
        "/api/admin/bookings",
        headers=bearer_headers(TEST_EDITOR_TOKEN),
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Admin claim required"}


def test_admin_can_list_bookings(admin_bookings_client: AdminBookingsClient) -> None:
    response = admin_bookings_client.client.get(
        "/api/admin/bookings",
        headers=_admin_headers(),
    )

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert {item["status"] for item in response.json()} == {"new", "contacted"}


def test_admin_can_filter_bookings_by_status(
    admin_bookings_client: AdminBookingsClient,
) -> None:
    response = admin_bookings_client.client.get(
        "/api/admin/bookings",
        headers=_admin_headers(),
        params={"status": "contacted"},
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": admin_bookings_client.contacted_booking_id,
            "package_id": admin_bookings_client.package_id,
            "package_title": "Safari Adventure",
            "availability_id": None,
            "customer_name": "Casey Contacted",
            "customer_email": "casey.contacted@example.com",
            "customer_phone": "+27 82 222 2222",
            "number_of_people": 4,
            "special_requests": None,
            "status": "contacted",
            "created_at": response.json()[0]["created_at"],
            "updated_at": response.json()[0]["updated_at"],
        }
    ]


def test_admin_can_view_booking_detail(
    admin_bookings_client: AdminBookingsClient,
) -> None:
    response = admin_bookings_client.client.get(
        f"/api/admin/bookings/{admin_bookings_client.booking_id}",
        headers=_admin_headers(),
    )

    assert response.status_code == 200
    assert response.json()["id"] == admin_bookings_client.booking_id
    assert response.json()["customer_email"] == "alex.new@example.com"


def test_admin_can_update_booking_status(
    admin_bookings_client: AdminBookingsClient,
) -> None:
    response = admin_bookings_client.client.patch(
        f"/api/admin/bookings/{admin_bookings_client.booking_id}/status",
        headers=_admin_headers(),
        json={"status": "confirmed"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "confirmed"


def test_invalid_status_returns_validation_error(
    admin_bookings_client: AdminBookingsClient,
) -> None:
    response = admin_bookings_client.client.patch(
        f"/api/admin/bookings/{admin_bookings_client.booking_id}/status",
        headers=_admin_headers(),
        json={"status": "pending"},
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "status"]


def test_admin_can_delete_booking(admin_bookings_client: AdminBookingsClient) -> None:
    delete_response = admin_bookings_client.client.delete(
        f"/api/admin/bookings/{admin_bookings_client.booking_id}",
        headers=_admin_headers(),
    )

    get_response = admin_bookings_client.client.get(
        f"/api/admin/bookings/{admin_bookings_client.booking_id}",
        headers=_admin_headers(),
    )

    assert delete_response.status_code == 204
    assert get_response.status_code == 404
    assert get_response.json() == {"detail": "Booking not found"}
