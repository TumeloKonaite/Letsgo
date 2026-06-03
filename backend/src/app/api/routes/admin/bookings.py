from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.api.schemas.bookings import BookingResponse, BookingStatusUpdateRequest
from app.core.dependencies import get_booking_service, require_admin
from app.domain.bookings.service import BookingNotFoundError, BookingService
from app.infrastructure.database.models import BookingStatus

router = APIRouter(
    prefix="/admin/bookings",
    tags=["admin-bookings"],
    dependencies=[Depends(require_admin)],
)


def _raise_for_booking_error(exc: Exception) -> None:
    if isinstance(exc, BookingNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        ) from exc
    raise exc


@router.get("", response_model=list[BookingResponse])
def list_bookings(
    service: Annotated[BookingService, Depends(get_booking_service)],
    booking_status: Annotated[BookingStatus | None, Query(alias="status")] = None,
) -> list[BookingResponse]:
    return service.list_bookings(status=booking_status)


@router.get("/{booking_id}", response_model=BookingResponse)
def get_booking(
    booking_id: int,
    service: Annotated[BookingService, Depends(get_booking_service)],
) -> BookingResponse:
    try:
        return service.get_booking(booking_id)
    except BookingNotFoundError as exc:
        _raise_for_booking_error(exc)


@router.patch("/{booking_id}/status", response_model=BookingResponse)
def update_booking_status(
    booking_id: int,
    payload: BookingStatusUpdateRequest,
    service: Annotated[BookingService, Depends(get_booking_service)],
) -> BookingResponse:
    try:
        return service.update_booking_status(booking_id, payload.status)
    except BookingNotFoundError as exc:
        _raise_for_booking_error(exc)


@router.delete("/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_booking(
    booking_id: int,
    service: Annotated[BookingService, Depends(get_booking_service)],
) -> Response:
    try:
        service.delete_booking(booking_id)
    except BookingNotFoundError as exc:
        _raise_for_booking_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
