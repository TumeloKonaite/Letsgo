from __future__ import annotations

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, joinedload, sessionmaker

from app.domain.bookings.repository import BookingRecord
from app.infrastructure.database.models import Booking, BookingStatus


class PostgresBookingRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

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
        with self._session_factory() as session:
            booking = session.get(Booking, booking_id)
            if booking is None:
                return None

            booking.status = status
            session.commit()

            statement = self._base_query().where(Booking.id == booking_id)
            refreshed_booking = session.scalars(statement).first()
            if refreshed_booking is None:
                return None
            return self._to_record(refreshed_booking)

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
