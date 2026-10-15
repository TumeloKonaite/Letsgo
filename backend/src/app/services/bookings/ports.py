"""Define persistence operations required by the booking service."""

from typing import Protocol

from app.services.bookings.models import BookingRecord, BookingStatus


class BookingRepository(Protocol):
    def list(self, *, status: BookingStatus | None = None) -> list[BookingRecord]:
        """Return bookings, optionally filtered by status."""

    def get_by_id(self, booking_id: int) -> BookingRecord | None:
        """Return one booking by id."""

    def update_status(
        self, booking_id: int, status: BookingStatus
    ) -> BookingRecord | None:
        """Update a booking status."""

    def delete(self, booking_id: int) -> bool:
        """Delete a booking."""
