"""Resolve application resources and separate bearer authentication from role checks."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.chatbot.service import TwinService
from app.core.config import Settings
from app.domain.auth.models import AuthenticatedUser
from app.domain.auth.provider import AuthenticationError, AuthenticationProvider
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


def get_authentication_provider(request: Request) -> AuthenticationProvider:
    """Return the configured provider-neutral token verifier."""
    return request.app.state.authentication_provider


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


def authentication_required() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_bearer_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> str:
    """Extract one bearer credential without interpreting its provider format."""
    if (
        credentials is None
        or credentials.scheme.lower() != "bearer"
        or not credentials.credentials
        or any(character.isspace() for character in credentials.credentials)
    ):
        raise authentication_required()
    return credentials.credentials


def get_current_user(
    token: Annotated[str, Depends(get_bearer_token)],
    provider: Annotated[AuthenticationProvider, Depends(get_authentication_provider)],
) -> AuthenticatedUser:
    """Authenticate through the configured provider boundary."""
    try:
        return provider.verify_token(token)
    except AuthenticationError:
        # Keep provider diagnostics out of responses and use one Bearer challenge.
        raise authentication_required() from None


def require_admin(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> AuthenticatedUser:
    """Apply the application's admin role rule after authentication."""
    if "admin" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return current_user
