from __future__ import annotations

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session, selectinload, sessionmaker

from app.domain.packages.repository import (
    AvailabilityItemRecord,
    ItineraryItemRecord,
    PackageDetailRecord,
    PackageImageRecord,
    PackageListItemRecord,
)
from app.infrastructure.database.models import Package, PackagePublicationStatus


class PostgresPackageRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list_published_packages(self) -> list[PackageListItemRecord]:
        with self._session_factory() as session:
            packages = session.scalars(self._published_package_query()).all()
            return [self._to_list_item(package) for package in packages]

    def get_published_package_by_slug(self, slug: str) -> PackageDetailRecord | None:
        with self._session_factory() as session:
            statement = self._published_package_query().where(Package.slug == slug)
            package = session.scalars(statement).first()
            if package is None:
                return None
            return self._to_detail(package)

    def _published_package_query(self) -> Select[tuple[Package]]:
        return (
            select(Package)
            .where(
                or_(
                    Package.status == PackagePublicationStatus.PUBLISHED,
                    Package.is_published.is_(True),
                )
            )
            .options(
                selectinload(Package.images),
                selectinload(Package.itinerary_items),
                selectinload(Package.availability_dates),
            )
            .order_by(
                Package.is_featured.desc(),
                Package.display_order.asc(),
                Package.created_at.desc(),
                Package.id.desc(),
            )
        )

    def _to_list_item(self, package: Package) -> PackageListItemRecord:
        return PackageListItemRecord(
            id=package.id,
            slug=package.slug,
            title=package.title,
            short_description=package.short_description,
            location=package.destination,
            duration_days=package.duration_days,
            price_from=package.price_from,
            currency=package.currency,
            is_featured=package.is_featured,
            images=tuple(self._to_image(image) for image in package.images),
        )

    def _to_detail(self, package: Package) -> PackageDetailRecord:
        return PackageDetailRecord(
            id=package.id,
            slug=package.slug,
            title=package.title,
            short_description=package.short_description,
            full_description=package.description,
            location=package.destination,
            duration_days=package.duration_days,
            price_from=package.price_from,
            currency=package.currency,
            is_featured=package.is_featured,
            images=tuple(self._to_image(image) for image in package.images),
            itinerary=tuple(self._to_itinerary_item(item) for item in package.itinerary_items),
            availability=tuple(self._to_availability_item(item) for item in package.availability_dates),
        )

    def _to_image(self, image) -> PackageImageRecord:
        return PackageImageRecord(
            id=image.id,
            image_url=image.image_url,
            alt_text=image.alt_text,
            sort_order=image.sort_order,
            is_cover=image.is_cover,
        )

    def _to_itinerary_item(self, item) -> ItineraryItemRecord:
        return ItineraryItemRecord(
            id=item.id,
            day_number=item.day_number,
            title=item.title,
            description=item.description,
            sort_order=item.sort_order,
        )

    def _to_availability_item(self, item) -> AvailabilityItemRecord:
        return AvailabilityItemRecord(
            id=item.id,
            start_date=item.start_date,
            end_date=item.end_date,
            capacity=item.capacity,
            spots_available=item.spots_available,
            status=item.status.value,
        )
