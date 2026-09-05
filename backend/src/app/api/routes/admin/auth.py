"""Expose normalized identity to signed-in users; admin access is checked separately."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.domain.auth.models import AuthenticatedUser

router = APIRouter(prefix="/admin/auth", tags=["admin-auth"])


@router.get("/me")
def get_authenticated_user(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> dict[str, object]:
    return {
        "sub": current_user.subject,
        "username": current_user.username,
        "email": current_user.email,
        "roles": sorted(current_user.roles),
        "provider": current_user.provider,
        "internal_user_id": current_user.internal_user_id,
    }
