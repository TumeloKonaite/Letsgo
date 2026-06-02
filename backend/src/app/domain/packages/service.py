from __future__ import annotations

from app.api.schemas.packages import (
    AvailabilityItem,
    ItineraryItem,
    PackageDetail,
    PackageImage,
    PackageListItem,
)
from app.domain.packages.repository import (
    AvailabilityItemRecord,
    ItineraryItemRecord,
    PackageDetailRecord,
    PackageImageRecord,
    PackageListItemRecord,
    PackageRepository,
)


class PackageNotFoundError(Exception):
    """Raised when a package is missing from the public catalog."""


class PackageService:
    def __init__(self, repository: PackageRepository) -> None:
        self._repository = repository

    def list_published_packages(self) -> list[PackageListItem]:
        return [self._to_list_item(package) for package in self._repository.list_published_packages()]

    def get_published_package_by_slug(self, slug: str) -> PackageDetail:
        package = self._repository.get_published_package_by_slug(slug)
        if package is None:
            raise PackageNotFoundError(slug)
        return self._to_detail(package)

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
            availability=[self._to_availability_item(item) for item in package.availability],
        )

    def _to_image(self, image: PackageImageRecord) -> PackageImage:
        return PackageImage(
            id=image.id,
            image_url=image.image_url,
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
            return cover_image.image_url
        if images:
            return images[0].image_url
        return None

    def _validate_package(self, price_from, duration_days: int) -> None:
        if price_from < 0:
            raise ValueError("Package price cannot be negative.")
        if duration_days <= 0:
            raise ValueError("Package duration must be greater than zero.")
