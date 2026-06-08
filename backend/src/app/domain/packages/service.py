from __future__ import annotations

from app.api.schemas.packages import (
    AvailabilityItem,
    ItineraryItem,
    PackageCreate,
    PackageDetail,
    PackageImage,
    PackageListItem,
    PackageResponse,
    PackageUpdate,
)
from app.domain.packages.repository import (
    AvailabilityItemRecord,
    ItineraryItemRecord,
    PackageCreateData,
    PackageDetailRecord,
    PackageImageRecord,
    PackageListItemRecord,
    PackageRecord,
    PackageRepository,
)
from app.domain.packages.storage import StorageError, StorageService


class PackageNotFoundError(Exception):
    """Raised when a package is missing."""


class DuplicatePackageSlugError(Exception):
    """Raised when a package slug is already in use."""


class PackageService:
    def __init__(
        self,
        repository: PackageRepository,
        storage_service: StorageService | None = None,
    ) -> None:
        self._repository = repository
        self._storage_service = storage_service

    def list_packages(self) -> list[PackageResponse]:
        return [
            self._to_package_response(package)
            for package in self._repository.list_all_packages()
        ]

    def get_package(self, package_id: int) -> PackageResponse:
        package = self._repository.get_by_id(package_id)
        if package is None:
            raise PackageNotFoundError(package_id)
        return self._to_package_response(package)

    def list_published_packages(self) -> list[PackageListItem]:
        return [
            self._to_list_item(package)
            for package in self._repository.list_published_packages()
        ]

    def get_published_package_by_slug(self, slug: str) -> PackageDetail:
        package = self._repository.get_published_package_by_slug(slug)
        if package is None:
            raise PackageNotFoundError(slug)
        return self._to_detail(package)

    def create_package(self, package_data: PackageCreate) -> PackageResponse:
        self._ensure_slug_is_unique(package_data.slug)
        package = self._repository.create(self._to_create_data(package_data))
        return self._to_package_response(package)

    def update_package(
        self, package_id: int, package_data: PackageUpdate
    ) -> PackageResponse:
        package = self._repository.get_by_id(package_id)
        if package is None:
            raise PackageNotFoundError(package_id)

        updates = package_data.model_dump(exclude_unset=True)
        new_slug = updates.get("slug")
        if isinstance(new_slug, str) and new_slug != package.slug:
            self._ensure_slug_is_unique(new_slug, exclude_package_id=package_id)

        if not updates:
            return self._to_package_response(package)

        updated_package = self._repository.update(package_id, updates)
        if updated_package is None:
            raise PackageNotFoundError(package_id)
        return self._to_package_response(updated_package)

    def publish_package(self, package_id: int) -> PackageResponse:
        package = self._repository.publish(package_id)
        if package is None:
            raise PackageNotFoundError(package_id)
        return self._to_package_response(package)

    def unpublish_package(self, package_id: int) -> PackageResponse:
        package = self._repository.unpublish(package_id)
        if package is None:
            raise PackageNotFoundError(package_id)
        return self._to_package_response(package)

    def delete_package(self, package_id: int) -> None:
        deleted = self._repository.delete(package_id)
        if not deleted:
            raise PackageNotFoundError(package_id)

    def _ensure_slug_is_unique(
        self, slug: str, exclude_package_id: int | None = None
    ) -> None:
        existing_package = self._repository.get_by_slug(slug)
        if existing_package is None:
            return
        if exclude_package_id is not None and existing_package.id == exclude_package_id:
            return
        raise DuplicatePackageSlugError(slug)

    def _to_create_data(self, package_data: PackageCreate) -> PackageCreateData:
        return PackageCreateData(
            title=package_data.title,
            slug=package_data.slug,
            short_description=package_data.short_description,
            description=package_data.description,
            destination=package_data.destination,
            duration_days=package_data.duration_days,
            duration_nights=package_data.duration_nights,
            price_from=package_data.price_from,
            currency=package_data.currency,
            is_active=package_data.is_active,
            status=package_data.status,
            is_published=package_data.is_published,
            is_featured=package_data.is_featured,
            display_order=package_data.display_order,
        )

    def _to_package_response(self, package: PackageRecord) -> PackageResponse:
        return PackageResponse(
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
        )

    def _to_list_item(self, package: PackageListItemRecord) -> PackageListItem:
        self._validate_package(package.price_from, package.duration_days)
        return PackageListItem(
            id=package.id,
            slug=package.slug,
            title=package.title,
            short_description=package.short_description,
            location=package.location,
            duration_days=package.duration_days,
            price_from=package.price_from,
            currency=package.currency,
            hero_image_url=self._hero_image_url(package.images),
            is_featured=package.is_featured,
        )

    def _to_detail(self, package: PackageDetailRecord) -> PackageDetail:
        self._validate_package(package.price_from, package.duration_days)
        return PackageDetail(
            id=package.id,
            slug=package.slug,
            title=package.title,
            short_description=package.short_description,
            full_description=package.full_description,
            location=package.location,
            duration_days=package.duration_days,
            price_from=package.price_from,
            currency=package.currency,
            hero_image_url=self._hero_image_url(package.images),
            is_featured=package.is_featured,
            images=[self._to_image(image) for image in package.images],
            itinerary=[self._to_itinerary_item(item) for item in package.itinerary],
            availability=[
                self._to_availability_item(item) for item in package.availability
            ],
        )

    def _to_image(self, image: PackageImageRecord) -> PackageImage:
        return PackageImage(
            id=image.id,
            image_url=self._resolve_image_url(image.image_url),
            alt_text=image.alt_text,
            sort_order=image.sort_order,
            is_cover=image.is_cover,
        )

    def _to_itinerary_item(self, item: ItineraryItemRecord) -> ItineraryItem:
        return ItineraryItem(
            id=item.id,
            day_number=item.day_number,
            title=item.title,
            description=item.description,
            sort_order=item.sort_order,
        )

    def _to_availability_item(self, item: AvailabilityItemRecord) -> AvailabilityItem:
        return AvailabilityItem(
            id=item.id,
            start_date=item.start_date,
            end_date=item.end_date,
            capacity=item.capacity,
            spots_available=item.spots_available,
            status=item.status,
        )

    def _hero_image_url(self, images: tuple[PackageImageRecord, ...]) -> str | None:
        cover_image = next((image for image in images if image.is_cover), None)
        if cover_image is not None:
            return self._resolve_image_url(cover_image.image_url)
        if images:
            return self._resolve_image_url(images[0].image_url)
        return None

    def _resolve_image_url(self, image_url: str) -> str:
        if self._storage_service is None:
            return image_url

        object_name = self._storage_service.extract_object_name(image_url)
        if object_name is None:
            return image_url

        try:
            return self._storage_service.get_public_url(object_name)
        except StorageError:
            return image_url

    def _validate_package(self, price_from, duration_days: int) -> None:
        if price_from < 0:
            raise ValueError("Package price cannot be negative.")
        if duration_days <= 0:
            raise ValueError("Package duration must be greater than zero.")
