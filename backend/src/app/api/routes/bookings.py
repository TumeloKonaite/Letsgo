"""Expose anonymous booking-request creation."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.schemas.bookings import BookingCreateRequest, BookingResponse
from app.core.dependencies import get_booking_service
from app.repository.postgres_booking_repository import (
    AvailabilityConflictError,
    AvailabilityNotFoundError,
    AvailabilityPackageMismatchError,
    PublicPackageNotFoundError,
)
from app.services.bookings.service import BookingService

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(
    payload: BookingCreateRequest,
    service: Annotated[BookingService, Depends(get_booking_service)],
) -> BookingResponse:
    try:
        return service.create_booking(payload)
    except PublicPackageNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Package not found") from exc
    except AvailabilityNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Departure not found") from exc
    except AvailabilityPackageMismatchError as exc:
        raise HTTPException(
            status_code=422, detail="Departure does not belong to the selected package"
        ) from exc
    except AvailabilityConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail="This departure no longer has enough available places.",
        ) from exc
