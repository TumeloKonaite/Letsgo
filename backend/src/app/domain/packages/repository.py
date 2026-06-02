from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Mapping, Protocol

from app.infrastructure.database.models import PackagePublicationStatus


@dataclass(frozen=True, slots=True)
class PackageImageRecord:
    id: int
    image_url: str
    alt_text: str | None
    sort_order: int
    is_cover: bool


@dataclass(frozen=True, slots=True)
class ItineraryItemRecord:
    id: int
    day_number: int
    title: str
    description: str
    sort_order: int


@dataclass(frozen=True, slots=True)
class AvailabilityItemRecord:
    id: int
    start_date: date
    end_date: date
    capacity: int
    spots_available: int
    status: str


@dataclass(frozen=True, slots=True)
class PackageListItemRecord:
    id: int
    slug: str
    title: str
    short_description: str | None
    location: str
    duration_days: int
    price_from: Decimal
    currency: str
    is_featured: bool
    images: tuple[PackageImageRecord, ...]


@dataclass(frozen=True, slots=True)
class PackageDetailRecord:
    id: int
    slug: str
    title: str
    short_description: str | None
    full_description: str
    location: str
    duration_days: int
    price_from: Decimal
    currency: str
    is_featured: bool
    images: tuple[PackageImageRecord, ...]
    itinerary: tuple[ItineraryItemRecord, ...]
    availability: tuple[AvailabilityItemRecord, ...]


@dataclass(frozen=True, slots=True)
class PackageRecord:
    id: int
    title: str
    slug: str
    short_description: str | None
    description: str
    destination: str
    duration_days: int
    duration_nights: int
    price_from: Decimal
    currency: str
    is_active: bool
    status: PackagePublicationStatus
    is_published: bool
    is_featured: bool
    display_order: int


@dataclass(frozen=True, slots=True)
class PackageCreateData:
    title: str
    slug: str
    short_description: str | None
    description: str
    destination: str
    duration_days: int
    duration_nights: int
    price_from: Decimal
    currency: str
    is_active: bool
    status: PackagePublicationStatus
    is_published: bool
    is_featured: bool
    display_order: int


class PackageRepository(Protocol):
    def list_published_packages(self) -> list[PackageListItemRecord]:
        """Return all publicly visible packages."""

    def get_published_package_by_slug(self, slug: str) -> PackageDetailRecord | None:
        """Return one publicly visible package by slug."""

    def create(self, package_data: PackageCreateData) -> PackageRecord:
        """Create a package."""

    def get_by_id(self, package_id: int) -> PackageRecord | None:
        """Return one package by id."""

    def get_by_slug(self, slug: str) -> PackageRecord | None:
        """Return one package by slug."""

    def update(
        self,
        package_id: int,
        package_data: Mapping[str, object],
    ) -> PackageRecord | None:
        """Apply a partial update to a package."""

    def publish(self, package_id: int) -> PackageRecord | None:
        """Publish a package."""

    def unpublish(self, package_id: int) -> PackageRecord | None:
        """Unpublish a package."""

    def delete(self, package_id: int) -> bool:
        """Delete a package."""
