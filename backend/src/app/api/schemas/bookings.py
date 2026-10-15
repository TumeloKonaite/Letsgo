"""Define booking response fields and the accepted admin status update payload."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.bookings.models import BookingStatus

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
MAX_BOOKING_GUESTS = 100


class BookingCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    package_id: int = Field(..., gt=0, strict=True)
    availability_id: int = Field(..., gt=0, strict=True)
    customer_name: str = Field(..., min_length=1, max_length=255)
    customer_email: str = Field(
        ..., min_length=3, max_length=320, pattern=EMAIL_PATTERN
    )
    customer_phone: str = Field(..., min_length=5, max_length=50)
    number_of_people: int = Field(..., gt=0, le=MAX_BOOKING_GUESTS, strict=True)
    special_requests: str | None = Field(default=None, max_length=2000)

    @field_validator("special_requests", mode="before")
    @classmethod
    def blank_special_requests_are_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class BookingResponse(BaseModel):
    id: int
    package_id: int
    package_title: str
    availability_id: int | None = None
    customer_name: str
    customer_email: str
    customer_phone: str
    number_of_people: int = Field(..., gt=0)
    special_requests: str | None = None
    status: BookingStatus
    created_at: datetime
    updated_at: datetime


class BookingStatusUpdateRequest(BaseModel):
    status: BookingStatus
