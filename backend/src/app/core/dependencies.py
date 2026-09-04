from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.clerk_auth import (
    ClerkAuthService,
    ClerkTokenExpiredError,
    ClerkTokenValidationError,
)
from app.chatbot.service import TwinService
from app.core.config import Settings
from app.domain.auth.models import AuthenticatedUser
from app.domain.bookings.repository import BookingRepository
from app.domain.bookings.service import BookingService
from app.domain.contact.repository import ContactRepository
from app.domain.contact.service import ContactService
from app.domain.packages.repository import PackageRepository
from app.domain.packages.service import PackageService
from app.domain.packages.storage import StorageService
from app.infrastructure.email.base import EmailSender

bearer_scheme = HTTPBearer(auto_error=False)


def get_settings(request: Request) -> Settings:
    """Return the validated settings attached during application startup."""
    return request.app.state.settings


def get_clerk_auth_service(request: Request) -> ClerkAuthService:
    """Return the shared Clerk token verifier."""
    return request.app.state.clerk_auth_service


def get_package_repository(request: Request) -> PackageRepository:
    """Return the shared package repository."""
    return request.app.state.package_repository


def get_package_service(request: Request) -> PackageService:
    """Return the package application service."""
    return request.app.state.package_service


def get_contact_repository(request: Request) -> ContactRepository:
    """Return the shared contact-submission repository."""
    return request.app.state.contact_repository


def get_contact_email_sender(request: Request) -> EmailSender:
    """Return the configured contact email adapter."""
    return request.app.state.contact_email_sender


def get_contact_service(request: Request) -> ContactService:
    """Return the contact application service."""
    return request.app.state.contact_service


def get_booking_repository(request: Request) -> BookingRepository:
    """Return the shared booking repository."""
    return request.app.state.booking_repository


def get_booking_service(request: Request) -> BookingService:
    """Return the booking application service."""
    return request.app.state.booking_service


def get_storage_service(request: Request) -> StorageService:
    """Return the configured object-storage adapter."""
    return request.app.state.storage_service


def get_twin_service(request: Request) -> TwinService:
    """Return the chatbot application service."""
    return request.app.state.chatbot_twin_service


def get_db_session(request: Request) -> Iterator[Session]:
    """Yield one database session and always close it after the request."""
    session_factory = request.app.state.db_session_factory
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    clerk_auth_service: Annotated[ClerkAuthService, Depends(get_clerk_auth_service)],
) -> AuthenticatedUser:
    """Authenticate a request from its Clerk bearer token."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )

    try:
        return clerk_auth_service.verify_token(credentials.credentials)
    except ClerkTokenExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        ) from exc
    except ClerkTokenValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from exc


def require_admin(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthenticatedUser:
    """Require the configured boolean admin claim on an authenticated user."""
    admin_claim = settings.clerk_admin_claim
    assert admin_claim is not None
    if current_user.claims.get(admin_claim) is not True:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin claim required",
        )
    return current_user
