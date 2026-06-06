from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.firebase_auth import (
    FirebaseAuthService,
    FirebaseTokenExpiredError,
    FirebaseTokenValidationError,
)
from app.core.config import Settings
from app.domain.bookings.repository import BookingRepository
from app.domain.bookings.service import BookingService
from app.domain.packages.repository import PackageRepository
from app.domain.packages.service import PackageService
from app.domain.packages.storage import StorageService
from app.domain.auth.models import AuthenticatedUser

bearer_scheme = HTTPBearer(auto_error=False)


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_firebase_auth_service(request: Request) -> FirebaseAuthService:
    return request.app.state.firebase_auth_service


def get_package_repository(request: Request) -> PackageRepository:
    return request.app.state.package_repository


def get_package_service(request: Request) -> PackageService:
    return request.app.state.package_service


def get_booking_repository(request: Request) -> BookingRepository:
    return request.app.state.booking_repository


def get_booking_service(request: Request) -> BookingService:
    return request.app.state.booking_service


def get_storage_service(request: Request) -> StorageService:
    return request.app.state.storage_service


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    firebase_auth_service: Annotated[FirebaseAuthService, Depends(get_firebase_auth_service)],
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )

    try:
        return firebase_auth_service.verify_token(credentials.credentials)
    except FirebaseTokenExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        ) from exc
    except FirebaseTokenValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from exc


def require_admin(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthenticatedUser:
    admin_claim = settings.firebase_admin_role
    if current_user.claims.get(admin_claim) is not True:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin claim required",
        )
    return current_user
