"""Validate public enquiries and delegate persistence and delivery to the contact service."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.schemas.contact import ContactRequest, ContactResponse
from app.core.dependencies import get_contact_service
from app.domain.contact import ContactService, ContactServiceError, ContactSubmission

router = APIRouter(prefix="/contact", tags=["contact"])


@router.post(
    "",
    response_model=ContactResponse,
    status_code=status.HTTP_200_OK,
)
def submit_contact_request(
    request: ContactRequest,
    contact_service: Annotated[ContactService, Depends(get_contact_service)],
) -> ContactResponse:
    try:
        contact_service.submit_contact_request(
            ContactSubmission(**request.model_dump())
        )
    except ContactServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to send contact request.",
        ) from exc

    return ContactResponse(message="Contact request submitted successfully.")
