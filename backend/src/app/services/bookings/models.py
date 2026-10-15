"""Define service-facing booking values and records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class BookingStatus(StrEnum):
    NEW = "new"
    CONTACTED = "contacted"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    CLOSED = "closed"


@dataclass(frozen=True, slots=True)
class BookingCreateData:
    package_id: int
    availability_id: int
    customer_name: str
    customer_email: str
    customer_phone: str
    number_of_people: int
    special_requests: str | None


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
