"""Define booking response fields and the accepted admin status update payload."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.infrastructure.database.models import BookingStatus


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
