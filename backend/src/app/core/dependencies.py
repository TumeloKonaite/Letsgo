from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings
from app.domain.packages.repository import PackageRepository
from app.domain.packages.service import PackageService
from app.core.keycloak import (
    KeycloakJWTValidator,
    TokenExpiredError,
    TokenValidationError,
)
from app.domain.auth.models import AuthenticatedUser

bearer_scheme = HTTPBearer(auto_error=False)


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_keycloak_auth_service(request: Request) -> KeycloakJWTValidator:
    return request.app.state.keycloak_auth_service


def get_package_repository(request: Request) -> PackageRepository:
    return request.app.state.package_repository


def get_package_service(request: Request) -> PackageService:
    return request.app.state.package_service


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    keycloak_auth_service: Annotated[KeycloakJWTValidator, Depends(get_keycloak_auth_service)],
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )

    try:
        return keycloak_auth_service.validate_token(credentials.credentials)
    except TokenExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        ) from exc
    except TokenValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from exc


def require_admin(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthenticatedUser:
    admin_role = settings.keycloak_admin_role or ""
    if admin_role not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return current_user
