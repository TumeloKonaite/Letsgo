from __future__ import annotations

from app.domain.packages.repository import PackageDetailRecord, PackageListItemRecord


class InMemoryPackageRepository:
    def __init__(self, packages: list[PackageDetailRecord] | None = None) -> None:
        self._packages = {package.slug: package for package in packages or []}

    def list_published_packages(self) -> list[PackageListItemRecord]:
        return [
            PackageListItemRecord(
                id=package.id,
                slug=package.slug,
                title=package.title,
                short_description=package.short_description,
                location=package.location,
                duration_days=package.duration_days,
                price_from=package.price_from,
                currency=package.currency,
                is_featured=package.is_featured,
                images=package.images,
            )
            for package in self._packages.values()
        ]

    def get_published_package_by_slug(self, slug: str) -> PackageDetailRecord | None:
        return self._packages.get(slug)
