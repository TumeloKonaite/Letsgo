"""PostgreSQL-only proof that concurrent public bookings cannot oversell."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from datetime import date, timedelta
from decimal import Decimal
from threading import Barrier
from uuid import uuid4

import pytest
from app.main import create_application
from app.repository.database.models import Booking, Package, PackageAvailability
from app.repository.database.models.package import PackageAvailabilityStatus
from app.services.packages.models import PackagePublicationStatus
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.engine import make_url

from tests.api.clerk_auth_helpers import build_test_settings


@pytest.mark.postgresql
def test_simultaneous_public_bookings_cannot_oversell():
    database_url = os.getenv("TEST_POSTGRESQL_DATABASE_URL")
    if not database_url:
        pytest.skip(
            "PostgreSQL contention test needs TEST_POSTGRESQL_DATABASE_URL; "
            "the dedicated CI integration step sets it explicitly"
        )
    assert make_url(database_url).get_backend_name() == "postgresql", (
        "The contention test must run against PostgreSQL; SQLite does not enforce row locks"
    )

    database_url = (
        make_url(database_url)
        .update_query_dict(
            {"options": "-c lock_timeout=5000 -c statement_timeout=10000"}
        )
        .render_as_string(hide_password=False)
    )
    engine_settings = build_test_settings(database_url)
    first_app = create_application(settings=engine_settings)
    second_app = create_application(settings=engine_settings)
    token = uuid4().hex
    slug = f"booking-contention-{token}"
    package_id: int | None = None
    first_engine = None
    second_engine = None
    try:
        with ExitStack() as stack:
            first_client = stack.enter_context(TestClient(first_app))
            second_client = stack.enter_context(TestClient(second_app))
            first_engine = first_app.state.db_session_factory.kw["bind"]
            second_engine = second_app.state.db_session_factory.kw["bind"]
            with first_app.state.db_session_factory() as session:
                package = Package(
                    title="Contention Safari",
                    slug=slug,
                    description="Integration test package.",
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
                    start_date=date.today() + timedelta(days=10),
                    end_date=date.today() + timedelta(days=12),
                    capacity=3,
                    spots_available=3,
                    status=PackageAvailabilityStatus.AVAILABLE,
                )
                session.add(availability)
                session.commit()
                package_id = package.id
                availability_id = availability.id

            barrier = Barrier(2, timeout=5)

            def send_booking(client: TestClient, suffix: str):
                barrier.wait(timeout=5)
                try:
                    return client.post(
                        "/api/bookings",
                        json={
                            "package_id": package_id,
                            "availability_id": availability_id,
                            "customer_name": f"Concurrent Guest {suffix}",
                            "customer_email": f"{suffix}@example.com",
                            "customer_phone": "+27 82 555 0100",
                            "number_of_people": 2,
                        },
                    )
                except Exception as exc:  # surface worker errors as test failures
                    pytest.fail(f"Concurrent booking request failed: {exc!r}")

            with ThreadPoolExecutor(max_workers=2) as executor:
                first = executor.submit(send_booking, first_client, "first")
                second = executor.submit(send_booking, second_client, "second")
                responses = [first.result(timeout=15), second.result(timeout=15)]

            assert sorted(response.status_code for response in responses) == [201, 409]
            successful = [
                response for response in responses if response.status_code == 201
            ]
            assert len(successful) == 1
            with first_app.state.db_session_factory() as session:
                availability = session.get(PackageAvailability, availability_id)
                bookings = session.scalars(
                    select(Booking).where(Booking.availability_id == availability_id)
                ).all()
                successful_places = sum(
                    response.json()["number_of_people"] for response in successful
                )
                assert availability.spots_available >= 0
                assert availability.spots_available == 3 - successful_places
                assert len(bookings) == len(successful) == 1
                assert (
                    sum(booking.number_of_people for booking in bookings)
                    == successful_places
                )
                assert all(booking.status.value == "new" for booking in bookings)
    finally:
        if first_engine is not None:
            if package_id is not None:
                with first_engine.begin() as connection:
                    connection.execute(
                        delete(Booking).where(Booking.package_id == package_id)
                    )
                    connection.execute(
                        delete(PackageAvailability).where(
                            PackageAvailability.package_id == package_id
                        )
                    )
                    connection.execute(delete(Package).where(Package.id == package_id))
            first_engine.dispose()
        if second_engine is not None:
            second_engine.dispose()
