from __future__ import annotations

from decimal import Decimal

import pytest

from app.api.schemas.packages import PackageCreate, PackageUpdate
from app.domain.packages.repository import PackageRecord
from app.domain.packages.service import (
    DuplicatePackageSlugError,
    PackageNotFoundError,
    PackageService,
)
from app.infrastructure.database.models import PackagePublicationStatus
from app.infrastructure.packages.in_memory_package_repository import InMemoryPackageRepository


def _build_service() -> PackageService:
    repository = InMemoryPackageRepository(
        packages=[
            PackageRecord(
                id=1,
                title="Existing Package",
                slug="existing-package",
                short_description="Existing package.",
                description="Existing package description.",
                destination="Cape Town",
                duration_days=4,
                duration_nights=3,
                price_from=Decimal("4500.00"),
                currency="ZAR",
                is_active=True,
                status=PackagePublicationStatus.DRAFT,
                is_published=False,
                is_featured=False,
                display_order=1,
            )
        ]
    )
    return PackageService(repository=repository)


def test_create_package_success() -> None:
    service = _build_service()

    package = service.create_package(
        PackageCreate(
            title="Garden Route Escape",
            slug="garden-route-escape",
            short_description="Coastal drive.",
            description="A multi-day Garden Route itinerary.",
            destination="Garden Route",
            duration_days=5,
            duration_nights=4,
            price_from=Decimal("6200.00"),
            currency="ZAR",
            is_active=True,
            status=PackagePublicationStatus.DRAFT,
            is_published=False,
            is_featured=True,
            display_order=2,
        )
    )

    assert package.id == 2
    assert package.slug == "garden-route-escape"


def test_create_package_duplicate_slug_fails() -> None:
    service = _build_service()

    with pytest.raises(DuplicatePackageSlugError):
        service.create_package(
            PackageCreate(
                title="Duplicate",
                slug="existing-package",
                short_description="Duplicate.",
                description="Duplicate slug should fail.",
                destination="Johannesburg",
                duration_days=3,
                duration_nights=2,
                price_from=Decimal("3000.00"),
                currency="ZAR",
                is_active=True,
                status=PackagePublicationStatus.DRAFT,
                is_published=False,
                is_featured=False,
                display_order=0,
            )
        )


def test_update_package_success() -> None:
    service = _build_service()

    package = service.update_package(
        1,
        PackageUpdate(
            title="Updated Package",
            price_from=Decimal("4999.00"),
        ),
    )

    assert package.title == "Updated Package"
    assert package.price_from == Decimal("4999.00")


def test_update_missing_package_fails() -> None:
    service = _build_service()

    with pytest.raises(PackageNotFoundError):
        service.update_package(999, PackageUpdate(title="Missing"))


def test_publish_package_success() -> None:
    service = _build_service()

    package = service.publish_package(1)

    assert package.status == PackagePublicationStatus.PUBLISHED
    assert package.is_published is True


def test_unpublish_package_success() -> None:
    service = _build_service()
    service.publish_package(1)

    package = service.unpublish_package(1)

    assert package.status == PackagePublicationStatus.DRAFT
    assert package.is_published is False


def test_delete_package_success() -> None:
    service = _build_service()

    service.delete_package(1)

    with pytest.raises(PackageNotFoundError):
        service.update_package(1, PackageUpdate(title="Deleted"))


def test_delete_missing_package_fails() -> None:
    service = _build_service()

    with pytest.raises(PackageNotFoundError):
        service.delete_package(999)
