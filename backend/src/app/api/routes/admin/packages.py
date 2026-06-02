from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session, sessionmaker

from app.api.schemas.packages import (
    AdminPackageImageCreateRequest,
    AdminPackageImageResponse,
    AdminPackagePutRequest,
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
from app.infrastructure.database.models import Package, PackageImage

router = APIRouter(
    prefix="/admin/packages",
    tags=["admin-packages"],
    dependencies=[Depends(require_admin)],
)


def get_session_factory(request: Request) -> sessionmaker[Session]:
    return request.app.state.db_session_factory


def _get_package_or_404(session: Session, package_id: int) -> Package:
    package = session.get(Package, package_id)
    if package is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Package not found",
        )
    return package


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


@router.post(
    "",
    response_model=PackageResponse,
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
    response_model=PackageResponse,
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
    response_model=PackageResponse,
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


@router.post(
    "/{package_id}/images",
    response_model=AdminPackageImageResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_package_image(
    package_id: int,
    payload: AdminPackageImageCreateRequest,
    session_factory: Annotated[sessionmaker[Session], Depends(get_session_factory)],
) -> AdminPackageImageResponse:
    with session_factory() as session:
        package = _get_package_or_404(session, package_id)
        image = PackageImage(**payload.model_dump())
        package.images.append(image)
        session.commit()
        session.refresh(image)
        return AdminPackageImageResponse(
            id=image.id,
            image_url=image.image_url,
            alt_text=image.alt_text,
            sort_order=image.sort_order,
            is_cover=image.is_cover,
        )


@router.delete(
    "/{package_id}/images",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_package_image(
    package_id: int,
    image_id: Annotated[int, Query(gt=0)],
    session_factory: Annotated[sessionmaker[Session], Depends(get_session_factory)],
) -> Response:
    with session_factory() as session:
        package = _get_package_or_404(session, package_id)
        image = next((candidate for candidate in package.images if candidate.id == image_id), None)
        if image is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Package image not found",
            )
        session.delete(image)
        session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
