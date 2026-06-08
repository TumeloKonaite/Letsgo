from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.infrastructure.database.models import BookingStatus


@dataclass(frozen=True, slots=True)
class BookingRecord:
    id: int
    package_id: int
    package_title: str
    availability_id: int | None
    customer_name: str
    customer_email: str
    customer_phone: str
    number_of_people: int
    special_requests: str | None
    status: BookingStatus
    created_at: datetime
    updated_at: datetime


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
