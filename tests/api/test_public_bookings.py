from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

import pytest
from app.api.schemas.bookings import BookingCreateRequest
from app.main import create_application
from app.repository.database.models import Booking, Package, PackageAvailability
from app.repository.database.models.package import PackageAvailabilityStatus
from app.services.bookings.models import BookingStatus
from app.services.bookings.service import InvalidBookingTransitionError
from app.services.packages.models import PackagePublicationStatus
from fastapi.testclient import TestClient
from sqlalchemy import event, select

from tests.api.clerk_auth_helpers import build_test_settings


@dataclass(frozen=True, slots=True)
class BookingFixture:
    client: TestClient
    session_factory: object
    package_id: int
    availability_id: int


@pytest.fixture
def booking_fixture(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'public-bookings.db'}"
    application = create_application(settings=build_test_settings(database_url))
    with (
        TestClient(application) as client,
        application.state.db_session_factory() as session,
    ):
        package = Package(
            title="Public Safari",
            slug="public-safari",
            description="A public safari.",
            destination="Kruger",
            duration_days=3,
            duration_nights=2,
            price_from=Decimal("5000.00"),
            is_active=True,
            status=PackagePublicationStatus.PUBLISHED,
            is_published=True,
        )
        session.add(package)
        session.flush()
        availability = PackageAvailability(
            package_id=package.id,
            start_date=date.today() + timedelta(days=5),
            end_date=date.today() + timedelta(days=7),
            capacity=3,
            spots_available=3,
            status=PackageAvailabilityStatus.AVAILABLE,
        )
        session.add(availability)
        session.commit()
        yield BookingFixture(
            client,
            application.state.db_session_factory,
            package.id,
            availability.id,
        )


def _payload(fixture: BookingFixture, **overrides):
    payload = {
        "package_id": fixture.package_id,
        "availability_id": fixture.availability_id,
        "customer_name": "  Amina Dlamini  ",
        "customer_email": "amina@example.com",
        "customer_phone": "  +27 82 555 0100  ",
        "number_of_people": 3,
        "special_requests": "   ",
    }
    payload.update(overrides)
    return payload


def test_anonymous_exact_capacity_booking_reserves_and_sells_out(booking_fixture):
    response = booking_fixture.client.post(
        "/api/bookings", json=_payload(booking_fixture)
    )

    assert response.status_code == 201
    assert response.json()["package_title"] == "Public Safari"
    assert response.json()["availability_id"] == booking_fixture.availability_id
    assert response.json()["customer_name"] == "Amina Dlamini"
    assert response.json()["special_requests"] is None
    assert response.json()["status"] == "new"
    with booking_fixture.session_factory() as session:
        availability = session.get(PackageAvailability, booking_fixture.availability_id)
        assert availability.spots_available == 0
        assert availability.status == PackageAvailabilityStatus.SOLD_OUT
        assert len(session.scalars(select(Booking)).all()) == 1


def test_insufficient_capacity_changes_nothing(booking_fixture):
    response = booking_fixture.client.post(
        "/api/bookings",
        json=_payload(booking_fixture, number_of_people=4),
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "This departure no longer has enough available places."
    }
    with booking_fixture.session_factory() as session:
        assert (
            session.get(
                PackageAvailability, booking_fixture.availability_id
            ).spots_available
            == 3
        )
        assert session.scalars(select(Booking)).all() == []


def test_unknown_request_field_is_rejected(booking_fixture):
    response = booking_fixture.client.post(
        "/api/bookings", json=_payload(booking_fixture, package_title="Fake")
    )
    assert response.status_code == 422


def test_cancellation_restores_inventory_once_and_is_terminal(booking_fixture):
    create_response = booking_fixture.client.post(
        "/api/bookings", json=_payload(booking_fixture, number_of_people=2)
    )
    booking_id = create_response.json()["id"]
    repository = booking_fixture.client.app.state.booking_repository

    repository.update_status(booking_id, BookingStatus.CANCELLED)
    repository.update_status(booking_id, BookingStatus.CANCELLED)

    with booking_fixture.session_factory() as session:
        availability = session.get(PackageAvailability, booking_fixture.availability_id)
        assert availability.spots_available == 3
    with pytest.raises(InvalidBookingTransitionError, match=str(booking_id)):
        repository.update_status(booking_id, BookingStatus.CONFIRMED)


def test_booking_insert_failure_rolls_back_capacity(booking_fixture):
    def fail_insert(*_args, **_kwargs):
        raise RuntimeError("synthetic insert failure")

    event.listen(Booking, "before_insert", fail_insert)
    try:
        with pytest.raises(RuntimeError, match="synthetic insert failure"):
            booking_fixture.client.app.state.booking_service.create_booking(
                BookingCreateRequest(**_payload(booking_fixture, number_of_people=2))
            )
    finally:
        event.remove(Booking, "before_insert", fail_insert)

    with booking_fixture.session_factory() as session:
        availability = session.get(PackageAvailability, booking_fixture.availability_id)
        assert availability.spots_available == 3
        assert session.scalars(select(Booking)).all() == []
