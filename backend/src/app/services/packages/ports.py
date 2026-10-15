"""Define persistence operations required by the package service."""

from collections.abc import Mapping
from typing import Protocol

from app.services.packages.models import (
    PackageCreateData,
    PackageDetailRecord,
    PackageListItemRecord,
    PackageRecord,
)


class PackageRepository(Protocol):
    def list_all_packages(self) -> list[PackageRecord]:
        """Return all packages for admin surfaces."""

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
