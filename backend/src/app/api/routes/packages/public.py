from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.schemas.packages import PackageDetail, PackageListItem
from app.core.dependencies import get_package_service
from app.domain.packages.service import PackageNotFoundError, PackageService

router = APIRouter(prefix="/packages", tags=["packages"])


@router.get("", response_model=list[PackageListItem])
def list_packages(
    service: Annotated[PackageService, Depends(get_package_service)],
) -> list[PackageListItem]:
    return service.list_published_packages()


@router.get(
    "/{slug}",
    response_model=PackageDetail,
    responses={status.HTTP_404_NOT_FOUND: {"description": "Package not found"}},
)
def get_package_detail(
    slug: str,
    service: Annotated[PackageService, Depends(get_package_service)],
) -> PackageDetail:
    try:
        return service.get_published_package_by_slug(slug)
    except PackageNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Package not found",
        ) from exc
