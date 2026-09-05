"""Implement package persistence in memory for isolated development and tests."""

from __future__ import annotations

from collections.abc import Mapping

from app.domain.packages.repository import (
    ItineraryItemData,
    ItineraryItemRecord,
    PackageCreateData,
    PackageDetailRecord,
    PackageInclusionData,
    PackageInclusionRecord,
    PackageListItemRecord,
    PackageRecord,
)
from app.infrastructure.database.models import PackagePublicationStatus


class InMemoryPackageRepository:
    def __init__(self, packages: list[PackageRecord] | None = None) -> None:
        seeded_packages = packages or []
        self._packages = {package.id: package for package in seeded_packages}
        self._next_id = max(self._packages, default=0) + 1
        self._next_itinerary_id = (
            max(
                (item.id for package in seeded_packages for item in package.itinerary),
                default=0,
            )
            + 1
        )
        self._next_inclusion_id = (
            max(
                (item.id for package in seeded_packages for item in package.inclusions),
                default=0,
            )
            + 1
        )

    def list_all_packages(self) -> list[PackageRecord]:
        return sorted(
            self._packages.values(),
            key=lambda package: (package.display_order, -package.id),
        )

    def create(self, package_data: PackageCreateData) -> PackageRecord:
        package = PackageRecord(
            id=self._next_id,
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
            itinerary=self._build_itinerary_records(package_data.itinerary),
            inclusions=self._build_inclusion_records(package_data.inclusions),
        )
        self._packages[package.id] = package
        self._next_id += 1
        return package

    def get_by_id(self, package_id: int) -> PackageRecord | None:
        return self._packages.get(package_id)

    def get_by_slug(self, slug: str) -> PackageRecord | None:
        return next(
            (package for package in self._packages.values() if package.slug == slug),
            None,
        )

    def update(
        self, package_id: int, package_data: Mapping[str, object]
    ) -> PackageRecord | None:
        package = self._packages.get(package_id)
        if package is None:
            return None

        updated_package = PackageRecord(
            id=package.id,
            title=package_data.get("title", package.title),
            slug=package_data.get("slug", package.slug),
            short_description=package_data.get(
                "short_description", package.short_description
            ),
            description=package_data.get("description", package.description),
            destination=package_data.get("destination", package.destination),
            duration_days=package_data.get("duration_days", package.duration_days),
            duration_nights=package_data.get(
                "duration_nights", package.duration_nights
            ),
            price_from=package_data.get("price_from", package.price_from),
            currency=package_data.get("currency", package.currency),
            is_active=package_data.get("is_active", package.is_active),
            status=package_data.get("status", package.status),
            is_published=package_data.get("is_published", package.is_published),
            is_featured=package_data.get("is_featured", package.is_featured),
            display_order=package_data.get("display_order", package.display_order),
            itinerary=self._build_itinerary_records(
                package_data.get("itinerary", package.itinerary)
            ),
            inclusions=self._build_inclusion_records(
                package_data.get("inclusions", package.inclusions)
            ),
        )
        self._packages[package_id] = updated_package
        return updated_package

    def publish(self, package_id: int) -> PackageRecord | None:
        return self.update(
            package_id,
            {
                "status": PackagePublicationStatus.PUBLISHED,
                "is_published": True,
            },
        )

    def unpublish(self, package_id: int) -> PackageRecord | None:
        return self.update(
            package_id,
            {
                "status": PackagePublicationStatus.DRAFT,
                "is_published": False,
            },
        )

    def delete(self, package_id: int) -> bool:
        removed = self._packages.pop(package_id, None)
        return removed is not None

    def list_published_packages(self) -> list[PackageListItemRecord]:
        published_packages = [
            package
            for package in self._packages.values()
            if package.status == PackagePublicationStatus.PUBLISHED
            or package.is_published
        ]
        return [
            PackageListItemRecord(
                id=package.id,
                slug=package.slug,
                title=package.title,
                short_description=package.short_description,
                location=package.destination,
                duration_days=package.duration_days,
                price_from=package.price_from,
                currency=package.currency,
                is_featured=package.is_featured,
                images=(),
            )
            for package in published_packages
        ]

    def get_published_package_by_slug(self, slug: str) -> PackageDetailRecord | None:
        package = self.get_by_slug(slug)
        if package is None:
            return None
        if (
            package.status != PackagePublicationStatus.PUBLISHED
            and not package.is_published
        ):
            return None
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
            images=(),
            itinerary=package.itinerary,
            inclusions=package.inclusions,
            availability=(),
        )

    def _build_itinerary_records(
        self, items: object
    ) -> tuple[ItineraryItemRecord, ...]:
        records: list[ItineraryItemRecord] = []
        for item in items or ():
            if isinstance(item, ItineraryItemRecord):
                records.append(item)
                continue

            if isinstance(item, ItineraryItemData):
                records.append(
                    ItineraryItemRecord(
                        id=self._next_itinerary_id,
                        title=item.title,
                        description=item.description,
                        duration=item.duration,
                        display_order=item.display_order,
                    )
                )
                self._next_itinerary_id += 1
        return tuple(records)

    def _build_inclusion_records(
        self, items: object
    ) -> tuple[PackageInclusionRecord, ...]:
        records: list[PackageInclusionRecord] = []
        for item in items or ():
            if isinstance(item, PackageInclusionRecord):
                records.append(item)
                continue

            if isinstance(item, PackageInclusionData):
                records.append(
                    PackageInclusionRecord(
                        id=self._next_inclusion_id,
                        name=item.name,
                        type=item.type,
                        display_order=item.display_order,
                    )
                )
                self._next_inclusion_id += 1
        return tuple(records)
