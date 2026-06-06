from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.infrastructure.database.session import verify_session_connection

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(request: Request) -> dict[str, str]:
    settings = request.app.state.settings
    return {
        "status": "ok",
        "application": settings.app_name,
        "environment": settings.environment,
    }


@router.get("/health/db")
def database_health_check(
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, str]:
    try:
        verify_session_connection(db)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        ) from exc

    return {
        "status": "ok",
        "database": "connected",
    }
