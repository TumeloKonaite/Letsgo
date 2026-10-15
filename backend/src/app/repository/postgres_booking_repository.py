"""Persist booking changes with SQLAlchemy and return service-facing records."""

from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, joinedload, sessionmaker

from app.repository.database.models import Booking, Package, PackageAvailability
from app.repository.database.models.package import PackageAvailabilityStatus
from app.services.bookings.models import BookingCreateData, BookingRecord, BookingStatus
from app.services.bookings.service import InvalidBookingTransitionError
from app.services.packages.models import PackagePublicationStatus

logger = logging.getLogger(__name__)


class PublicPackageNotFoundError(Exception):
    """Raised when the selected package is not publicly bookable."""


class AvailabilityNotFoundError(Exception):
    """Raised when the selected departure does not exist."""


class AvailabilityPackageMismatchError(Exception):
    """Raised when the departure belongs to another package."""


class AvailabilityConflictError(Exception):
    """Raised when a departure cannot accept the requested party."""


class PostgresBookingRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create(self, data: BookingCreateData) -> BookingRecord:
        with self._session_factory() as session, session.begin():
            package = session.scalar(
                select(Package).where(Package.id == data.package_id).with_for_update()
            )
            if (
                package is None
                or not package.is_active
                or not package.is_published
                or package.status != PackagePublicationStatus.PUBLISHED
            ):
                raise PublicPackageNotFoundError(data.package_id)

            availability = session.scalar(
                select(PackageAvailability)
                .where(PackageAvailability.id == data.availability_id)
                .with_for_update()
            )
            if availability is None:
                raise AvailabilityNotFoundError(data.availability_id)
            if availability.package_id != package.id:
                raise AvailabilityPackageMismatchError(data.availability_id)
            if (
                availability.status != PackageAvailabilityStatus.AVAILABLE
                or availability.start_date < date.today()
                or availability.spots_available < data.number_of_people
            ):
                raise AvailabilityConflictError(data.availability_id)

            availability.spots_available -= data.number_of_people
            if availability.spots_available == 0:
                availability.status = PackageAvailabilityStatus.SOLD_OUT

            booking = Booking(
                package_id=package.id,
                availability_id=availability.id,
                customer_name=data.customer_name,
                customer_email=data.customer_email,
                customer_phone=data.customer_phone,
                number_of_people=data.number_of_people,
                special_requests=data.special_requests,
                status=BookingStatus.NEW,
            )
            session.add(booking)
            session.flush()
            session.refresh(booking)
            return self._to_record(booking)

    def list(self, *, status: BookingStatus | None = None) -> list[BookingRecord]:
        with self._session_factory() as session:
            statement = self._base_query()
            if status is not None:
                statement = statement.where(Booking.status == status)
            bookings = session.scalars(statement).all()
            return [self._to_record(booking) for booking in bookings]

    def get_by_id(self, booking_id: int) -> BookingRecord | None:
        with self._session_factory() as session:
            statement = self._base_query().where(Booking.id == booking_id)
            booking = session.scalars(statement).first()
            if booking is None:
                return None
            return self._to_record(booking)

    def update_status(
        self, booking_id: int, status: BookingStatus
    ) -> BookingRecord | None:
        with self._session_factory() as session, session.begin():
            booking = session.scalar(
                select(Booking).where(Booking.id == booking_id).with_for_update()
            )
            if booking is None:
                return None

            if (
                booking.status == BookingStatus.CANCELLED
                and status != BookingStatus.CANCELLED
            ):
                raise InvalidBookingTransitionError(booking_id)

            if (
                status == BookingStatus.CANCELLED
                and booking.status != BookingStatus.CANCELLED
                and booking.availability_id is not None
            ):
                availability = session.scalar(
                    select(PackageAvailability)
                    .where(PackageAvailability.id == booking.availability_id)
                    .with_for_update()
                )
                if availability is not None:
                    restored_spots = (
                        availability.spots_available + booking.number_of_people
                    )
                    if restored_spots > availability.capacity:
                        logger.warning(
                            "Booking cancellation inventory restore exceeded capacity",
                            extra={
                                "booking_id": booking.id,
                                "availability_id": availability.id,
                                "restored_spots": restored_spots,
                                "capacity": availability.capacity,
                            },
                        )
                    availability.spots_available = min(
                        availability.capacity,
                        restored_spots,
                    )
                    if (
                        availability.status == PackageAvailabilityStatus.SOLD_OUT
                        and availability.spots_available > 0
                    ):
                        availability.status = PackageAvailabilityStatus.AVAILABLE

            booking.status = status
            session.flush()
            session.refresh(booking)
            return self._to_record(booking)

    def delete(self, booking_id: int) -> bool:
        with self._session_factory() as session:
            booking = session.get(Booking, booking_id)
            if booking is None:
                return False

            session.delete(booking)
            session.commit()
            return True

    def _base_query(self) -> Select[tuple[Booking]]:
        return (
            select(Booking)
            .options(joinedload(Booking.package))
            .order_by(Booking.created_at.desc(), Booking.id.desc())
        )

    def _to_record(self, booking: Booking) -> BookingRecord:
        return BookingRecord(
            id=booking.id,
            package_id=booking.package_id,
            package_title=booking.package.title,
            availability_id=booking.availability_id,
            customer_name=booking.customer_name,
            customer_email=booking.customer_email,
            customer_phone=booking.customer_phone,
            number_of_people=booking.number_of_people,
            special_requests=booking.special_requests,
            status=booking.status,
            created_at=booking.created_at,
            updated_at=booking.updated_at,
        )
