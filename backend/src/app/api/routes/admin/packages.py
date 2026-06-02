from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session, sessionmaker

from app.api.schemas.packages import (
    AdminPackageCreateRequest,
    AdminPackageImageCreateRequest,
    AdminPackageImageResponse,
    AdminPackagePatchRequest,
    AdminPackagePutRequest,
    AdminPackageResponse,
)
from app.core.dependencies import require_admin
from app.domain.auth.models import AuthenticatedUser
from app.infrastructure.database.models import Package, PackageImage

router = APIRouter(prefix="/admin/packages", tags=["admin-packages"])


def get_session_factory(request: Request) -> sessionmaker[Session]:
    return request.app.state.db_session_factory


def _package_to_response(package: Package) -> AdminPackageResponse:
    return AdminPackageResponse(
        id=package.id,
        title=package.title,
        slug=package.slug,
        short_description=package.short_description,
        description=package.description,
        destination=package.destination,
        duration_days=package.duration_days,
        duration_nights=package.duration_nights,
        price_from=package.price_from,
        currency=package.currency,
        is_active=package.is_active,
        status=package.status,
        is_published=package.is_published,
        is_featured=package.is_featured,
        display_order=package.display_order,
        images=[
            AdminPackageImageResponse(
                id=image.id,
                image_url=image.image_url,
                alt_text=image.alt_text,
                sort_order=image.sort_order,
                is_cover=image.is_cover,
            )
            for image in package.images
        ],
    )


def _get_package_or_404(session: Session, package_id: int) -> Package:
    package = session.get(Package, package_id)
    if package is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Package not found",
        )
    return package


def _apply_package_payload(
    package: Package,
    payload: AdminPackageCreateRequest | AdminPackagePutRequest | dict[str, object],
) -> None:
    data = payload.model_dump() if hasattr(payload, "model_dump") else payload
    for field_name, value in data.items():
        setattr(package, field_name, value)


@router.post(
    "",
    response_model=AdminPackageResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_package(
    payload: AdminPackageCreateRequest,
    session_factory: Annotated[sessionmaker[Session], Depends(get_session_factory)],
    current_user: Annotated[AuthenticatedUser, Depends(require_admin)],
) -> AdminPackageResponse:
    del current_user
    with session_factory() as session:
        package = Package()
        _apply_package_payload(package, payload)
        session.add(package)
        session.commit()
        session.refresh(package)
        return _package_to_response(package)


@router.put(
    "/{package_id}",
    response_model=AdminPackageResponse,
)
def replace_package(
    package_id: int,
    payload: AdminPackagePutRequest,
    session_factory: Annotated[sessionmaker[Session], Depends(get_session_factory)],
    current_user: Annotated[AuthenticatedUser, Depends(require_admin)],
) -> AdminPackageResponse:
    del current_user
    with session_factory() as session:
        package = _get_package_or_404(session, package_id)
        _apply_package_payload(package, payload)
        session.commit()
        session.refresh(package)
        return _package_to_response(package)


@router.patch(
    "/{package_id}",
    response_model=AdminPackageResponse,
)
def update_package(
    package_id: int,
    payload: AdminPackagePatchRequest,
    session_factory: Annotated[sessionmaker[Session], Depends(get_session_factory)],
    current_user: Annotated[AuthenticatedUser, Depends(require_admin)],
) -> AdminPackageResponse:
    del current_user
    with session_factory() as session:
        package = _get_package_or_404(session, package_id)
        _apply_package_payload(package, payload.model_dump(exclude_unset=True))
        session.commit()
        session.refresh(package)
        return _package_to_response(package)


@router.delete(
    "/{package_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_package(
    package_id: int,
    session_factory: Annotated[sessionmaker[Session], Depends(get_session_factory)],
    current_user: Annotated[AuthenticatedUser, Depends(require_admin)],
) -> Response:
    del current_user
    with session_factory() as session:
        package = _get_package_or_404(session, package_id)
        session.delete(package)
        session.commit()
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
    current_user: Annotated[AuthenticatedUser, Depends(require_admin)],
) -> AdminPackageImageResponse:
    del current_user
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
    current_user: Annotated[AuthenticatedUser, Depends(require_admin)],
) -> Response:
    del current_user
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
