"""Expose package management and publication actions behind the admin role check."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.schemas.packages import (
    AdminPackagePutRequest,
    AdminPackageResponse,
    PackageCreate,
    PackageResponse,
    PackageUpdate,
)
from app.core.dependencies import get_package_service, require_admin
from app.domain.packages.service import (
    DuplicatePackageSlugError,
    PackageNotFoundError,
    PackageService,
)

router = APIRouter(
    prefix="/admin/packages",
    tags=["admin-packages"],
    dependencies=[Depends(require_admin)],
)


def _raise_for_package_error(exc: Exception) -> None:
    if isinstance(exc, DuplicatePackageSlugError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Package slug already exists",
        ) from exc
    if isinstance(exc, PackageNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Package not found",
        ) from exc
    raise exc


@router.get(
    "",
    response_model=list[PackageResponse],
)
def list_packages(
    service: Annotated[PackageService, Depends(get_package_service)],
) -> list[PackageResponse]:
    return service.list_packages()


@router.get(
    "/{package_id}",
    response_model=AdminPackageResponse,
)
def get_package(
    package_id: int,
    service: Annotated[PackageService, Depends(get_package_service)],
) -> PackageResponse:
    try:
        return service.get_package(package_id)
    except PackageNotFoundError as exc:
        _raise_for_package_error(exc)


@router.post(
    "",
    response_model=AdminPackageResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_package(
    payload: PackageCreate,
    service: Annotated[PackageService, Depends(get_package_service)],
) -> PackageResponse:
    try:
        return service.create_package(payload)
    except DuplicatePackageSlugError as exc:
        _raise_for_package_error(exc)


@router.put(
    "/{package_id}",
    response_model=AdminPackageResponse,
)
def replace_package(
    package_id: int,
    payload: AdminPackagePutRequest,
    service: Annotated[PackageService, Depends(get_package_service)],
) -> PackageResponse:
    try:
        return service.update_package(
            package_id,
            PackageUpdate.model_validate(payload.model_dump()),
        )
    except (DuplicatePackageSlugError, PackageNotFoundError) as exc:
        _raise_for_package_error(exc)


@router.patch(
    "/{package_id}",
    response_model=AdminPackageResponse,
)
def update_package(
    package_id: int,
    payload: PackageUpdate,
    service: Annotated[PackageService, Depends(get_package_service)],
) -> PackageResponse:
    try:
        return service.update_package(package_id, payload)
    except (DuplicatePackageSlugError, PackageNotFoundError) as exc:
        _raise_for_package_error(exc)


@router.patch(
    "/{package_id}/publish",
    response_model=PackageResponse,
)
def publish_package(
    package_id: int,
    service: Annotated[PackageService, Depends(get_package_service)],
) -> PackageResponse:
    try:
        return service.publish_package(package_id)
    except PackageNotFoundError as exc:
        _raise_for_package_error(exc)


@router.patch(
    "/{package_id}/unpublish",
    response_model=PackageResponse,
)
def unpublish_package(
    package_id: int,
    service: Annotated[PackageService, Depends(get_package_service)],
) -> PackageResponse:
    try:
        return service.unpublish_package(package_id)
    except PackageNotFoundError as exc:
        _raise_for_package_error(exc)


@router.delete(
    "/{package_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_package(
    package_id: int,
    service: Annotated[PackageService, Depends(get_package_service)],
) -> Response:
    try:
        service.delete_package(package_id)
    except PackageNotFoundError as exc:
        _raise_for_package_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
