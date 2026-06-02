from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile, status
from sqlalchemy.orm import Session, sessionmaker

from app.api.schemas.packages import AdminPackageImageResponse
from app.core.config import Settings
from app.core.dependencies import get_settings, get_storage_service, require_admin
from app.domain.packages.storage import (
    ImageTooLargeError,
    InvalidImageFormatError,
    StorageAuthenticationError,
    StorageBucketNotFoundError,
    StorageError,
    StorageService,
    build_package_image_object_name,
    validate_image_upload,
)
from app.infrastructure.database.models import Package, PackageImage

router = APIRouter(
    prefix="/admin/packages",
    tags=["admin-package-images"],
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


def _next_display_order(package: Package) -> int:
    if not package.images:
        return 0
    return max(image.sort_order for image in package.images) + 1


def _to_response(image: PackageImage, storage_service: StorageService) -> AdminPackageImageResponse:
    object_name = image.storage_key or storage_service.extract_object_name(image.image_url)
    url = image.image_url if object_name is None else storage_service.get_presigned_url(object_name)
    return AdminPackageImageResponse(
        id=image.id,
        package_id=image.package_id,
        url=url,
        alt_text=image.alt_text,
        display_order=image.sort_order,
        is_cover=image.is_cover,
    )


def _raise_for_storage_error(exc: StorageError) -> None:
    if isinstance(exc, StorageAuthenticationError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Image storage authentication failed",
        ) from exc
    if isinstance(exc, StorageBucketNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Image storage bucket not found",
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Image storage request failed",
    ) from exc


@router.post(
    "/{package_id}/images",
    response_model=AdminPackageImageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_package_image(
    package_id: int,
    file: Annotated[UploadFile, File(...)],
    session_factory: Annotated[sessionmaker[Session], Depends(get_session_factory)],
    storage_service: Annotated[StorageService, Depends(get_storage_service)],
    settings: Annotated[Settings, Depends(get_settings)],
    alt_text: Annotated[str | None, Form()] = None,
    display_order: Annotated[int | None, Form(ge=0)] = None,
    is_cover: Annotated[bool, Form()] = False,
) -> AdminPackageImageResponse:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image file is required",
        )

    content = await file.read()
    try:
        content_type = validate_image_upload(content, settings.package_image_max_upload_bytes)
    except (InvalidImageFormatError, ImageTooLargeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    finally:
        await file.close()

    with session_factory() as session:
        package = _get_package_or_404(session, package_id)
        object_name = build_package_image_object_name(
            package.slug,
            file.filename,
            content_type,
        )

        try:
            stored_object = storage_service.upload_image(object_name, content, content_type)
        except StorageError as exc:
            _raise_for_storage_error(exc)

        image = PackageImage(
            package_id=package.id,
            storage_key=stored_object.object_name,
            image_url=stored_object.url,
            alt_text=alt_text,
            sort_order=display_order if display_order is not None else _next_display_order(package),
            is_cover=is_cover,
        )
        if image.is_cover:
            for existing_image in package.images:
                existing_image.is_cover = False

        try:
            session.add(image)
            session.commit()
            session.refresh(image)
        except Exception:
            session.rollback()
            try:
                storage_service.delete_image(stored_object.object_name)
            except StorageError:
                pass
            raise

        return _to_response(image, storage_service)


@router.get(
    "/{package_id}/images",
    response_model=list[AdminPackageImageResponse],
)
def list_package_images(
    package_id: int,
    session_factory: Annotated[sessionmaker[Session], Depends(get_session_factory)],
    storage_service: Annotated[StorageService, Depends(get_storage_service)],
) -> list[AdminPackageImageResponse]:
    with session_factory() as session:
        package = _get_package_or_404(session, package_id)
        return [_to_response(image, storage_service) for image in package.images]


@router.delete(
    "/{package_id}/images/{image_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_package_image(
    package_id: int,
    image_id: int,
    session_factory: Annotated[sessionmaker[Session], Depends(get_session_factory)],
    storage_service: Annotated[StorageService, Depends(get_storage_service)],
) -> Response:
    with session_factory() as session:
        package = _get_package_or_404(session, package_id)
        image = next((candidate for candidate in package.images if candidate.id == image_id), None)
        if image is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Package image not found",
            )

        object_name = image.storage_key or storage_service.extract_object_name(image.image_url)
        if object_name is not None:
            try:
                storage_service.delete_image(object_name)
            except StorageError as exc:
                _raise_for_storage_error(exc)

        session.delete(image)
        session.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
