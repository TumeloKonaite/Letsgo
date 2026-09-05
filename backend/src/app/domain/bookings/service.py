"""Apply booking lookup and update workflows, translating records into API responses."""

from __future__ import annotations

from app.api.schemas.bookings import BookingResponse
from app.domain.bookings.repository import BookingRecord, BookingRepository
from app.infrastructure.database.models import BookingStatus


class BookingNotFoundError(Exception):
    """Raised when a booking is missing."""


class BookingService:
    def __init__(self, repository: BookingRepository) -> None:
        self._repository = repository

    def list_bookings(
        self, *, status: BookingStatus | None = None
    ) -> list[BookingResponse]:
        return [
            self._to_response(booking)
            for booking in self._repository.list(status=status)
        ]

    def get_booking(self, booking_id: int) -> BookingResponse:
        booking = self._repository.get_by_id(booking_id)
        if booking is None:
            raise BookingNotFoundError(booking_id)
        return self._to_response(booking)

    def update_booking_status(
        self,
        booking_id: int,
        status: BookingStatus,
    ) -> BookingResponse:
        booking = self._repository.update_status(booking_id, status)
        if booking is None:
            raise BookingNotFoundError(booking_id)
        return self._to_response(booking)

    def delete_booking(self, booking_id: int) -> None:
        deleted = self._repository.delete(booking_id)
        if not deleted:
            raise BookingNotFoundError(booking_id)

    def _to_response(self, booking: BookingRecord) -> BookingResponse:
        return BookingResponse(
            id=booking.id,
            package_id=booking.package_id,
            package_title=booking.package_title,
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
