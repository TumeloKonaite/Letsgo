from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

import pytest
from app.api.schemas.bookings import MAX_BOOKING_GUESTS, BookingCreateRequest
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
        package = _new_package()
        session.add(package)
        session.flush()
        availability = _new_availability(package.id)
        session.add(availability)
        session.commit()
        yield BookingFixture(
            client,
            application.state.db_session_factory,
            package.id,
            availability.id,
        )


def _new_package(**overrides) -> Package:
    values = {
        "title": "Public Safari",
        "slug": "public-safari",
        "description": "A public safari.",
        "destination": "Kruger",
        "duration_days": 3,
        "duration_nights": 2,
        "price_from": Decimal("5000.00"),
        "is_active": True,
        "status": PackagePublicationStatus.PUBLISHED,
        "is_published": True,
    }
    values.update(overrides)
    return Package(**values)


def _new_availability(package_id: int, **overrides) -> PackageAvailability:
    values = {
        "package_id": package_id,
        "start_date": date.today() + timedelta(days=5),
        "end_date": date.today() + timedelta(days=7),
        "capacity": 3,
        "spots_available": 3,
        "status": PackageAvailabilityStatus.AVAILABLE,
    }
    values.update(overrides)
    return PackageAvailability(**values)


def _payload(fixture: BookingFixture, **overrides):
    payload = {
        "package_id": fixture.package_id,
        "availability_id": fixture.availability_id,
        "customer_name": "  Amina Dlamini  ",
        "customer_email": "  amina@example.com  ",
        "customer_phone": "  +27 82 555 0100  ",
        "number_of_people": 2,
        "special_requests": "   ",
    }
    payload.update(overrides)
    return payload


def _assert_unchanged(fixture: BookingFixture) -> None:
    with fixture.session_factory() as session:
        availability = session.get(PackageAvailability, fixture.availability_id)
        assert availability.spots_available == 3
        assert availability.status == PackageAvailabilityStatus.AVAILABLE
        assert session.scalars(select(Booking)).all() == []


def test_anonymous_booking_uses_server_facts_and_creates_new_booking(booking_fixture):
    response = booking_fixture.client.post(
        "/api/bookings",
        json=_payload(booking_fixture, special_requests="  Window seat, please.  "),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["package_id"] == booking_fixture.package_id
    assert body["package_title"] == "Public Safari"
    assert body["availability_id"] == booking_fixture.availability_id
    assert body["customer_name"] == "Amina Dlamini"
    assert body["customer_email"] == "amina@example.com"
    assert body["customer_phone"] == "+27 82 555 0100"
    assert body["special_requests"] == "Window seat, please."
    assert body["status"] == "new"
    with booking_fixture.session_factory() as session:
        booking = session.scalar(select(Booking))
        assert booking is not None
        assert booking.status == BookingStatus.NEW
        assert booking.package.title == "Public Safari"
        assert booking.availability_id == booking_fixture.availability_id
        assert (
            session.get(
                PackageAvailability, booking_fixture.availability_id
            ).spots_available
            == 1
        )


def test_exact_capacity_booking_reserves_and_sells_out(booking_fixture):
    response = booking_fixture.client.post(
        "/api/bookings", json=_payload(booking_fixture, number_of_people=3)
    )

    assert response.status_code == 201
    assert response.json()["status"] == "new"
    with booking_fixture.session_factory() as session:
        availability = session.get(PackageAvailability, booking_fixture.availability_id)
        assert availability.spots_available == 0
        assert availability.status == PackageAvailabilityStatus.SOLD_OUT
        assert len(session.scalars(select(Booking)).all()) == 1


@pytest.mark.parametrize(
    ("id_field", "unknown_id", "detail"),
    [
        ("package_id", 999_999, "Package not found"),
        ("availability_id", 999_999, "Departure not found"),
    ],
)
def test_unknown_package_or_departure_returns_404(
    booking_fixture, id_field, unknown_id, detail
):
    response = booking_fixture.client.post(
        "/api/bookings", json=_payload(booking_fixture, **{id_field: unknown_id})
    )

    assert response.status_code == 404
    assert response.json() == {"detail": detail}
    _assert_unchanged(booking_fixture)


def test_departure_for_another_package_is_rejected(booking_fixture):
    with booking_fixture.session_factory() as session:
        other_package = _new_package(title="Other", slug="other")
        session.add(other_package)
        session.flush()
        other_availability = _new_availability(other_package.id)
        session.add(other_availability)
        session.commit()
        other_availability_id = other_availability.id

    response = booking_fixture.client.post(
        "/api/bookings",
        json=_payload(booking_fixture, availability_id=other_availability_id),
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Departure does not belong to the selected package"
    }
    _assert_unchanged(booking_fixture)


@pytest.mark.parametrize(
    "package_changes",
    [
        {"is_active": False},
        {"is_published": False},
        {"status": PackagePublicationStatus.DRAFT},
    ],
)
def test_non_public_package_cannot_be_booked(booking_fixture, package_changes):
    with booking_fixture.session_factory() as session:
        package = session.get(Package, booking_fixture.package_id)
        for field, value in package_changes.items():
            setattr(package, field, value)
        session.commit()

    response = booking_fixture.client.post(
        "/api/bookings", json=_payload(booking_fixture)
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Package not found"}
    _assert_unchanged(booking_fixture)


@pytest.mark.parametrize(
    "availability_changes",
    [
        {"status": PackageAvailabilityStatus.CLOSED},
        {"status": PackageAvailabilityStatus.SOLD_OUT, "spots_available": 0},
        {
            "start_date": date.today() - timedelta(days=2),
            "end_date": date.today() - timedelta(days=1),
        },
    ],
)
def test_unavailable_departure_returns_conflict(booking_fixture, availability_changes):
    with booking_fixture.session_factory() as session:
        availability = session.get(PackageAvailability, booking_fixture.availability_id)
        for field, value in availability_changes.items():
            setattr(availability, field, value)
        session.commit()
        expected_spots = availability.spots_available
        expected_status = availability.status

    response = booking_fixture.client.post(
        "/api/bookings", json=_payload(booking_fixture, number_of_people=1)
    )

    assert response.status_code == 409
    with booking_fixture.session_factory() as session:
        availability = session.get(PackageAvailability, booking_fixture.availability_id)
        assert availability.spots_available == expected_spots
        assert availability.status == expected_status
        assert session.scalars(select(Booking)).all() == []


def test_insufficient_capacity_changes_nothing(booking_fixture):
    response = booking_fixture.client.post(
        "/api/bookings",
        json=_payload(booking_fixture, number_of_people=4),
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "This departure no longer has enough available places."
    }
    _assert_unchanged(booking_fixture)


@pytest.mark.parametrize(
    ("overrides", "removed_field"),
    [
        ({"customer_name": "   "}, None),
        ({"customer_email": "   "}, None),
        ({"customer_phone": "   "}, None),
        ({"customer_email": "not-an-email"}, None),
        ({"number_of_people": 0}, None),
        ({"number_of_people": -1}, None),
        ({"number_of_people": MAX_BOOKING_GUESTS + 1}, None),
        ({"customer_name": "n" * 256}, None),
        ({"customer_email": f"{'e' * 309}@example.com"}, None),
        ({"customer_phone": "1" * 51}, None),
        ({"special_requests": "r" * 2001}, None),
        ({"package_title": "Browser-supplied title"}, None),
        ({}, "customer_name"),
    ],
)
def test_malformed_input_returns_422(booking_fixture, overrides, removed_field):
    payload = _payload(booking_fixture, **overrides)
    if removed_field is not None:
        payload.pop(removed_field)

    response = booking_fixture.client.post("/api/bookings", json=payload)

    assert response.status_code == 422
    _assert_unchanged(booking_fixture)


def test_blank_optional_special_requests_are_stored_as_null(booking_fixture):
    response = booking_fixture.client.post(
        "/api/bookings", json=_payload(booking_fixture)
    )

    assert response.status_code == 201
    assert response.json()["special_requests"] is None
    with booking_fixture.session_factory() as session:
        assert session.scalar(select(Booking)).special_requests is None


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

    _assert_unchanged(booking_fixture)
