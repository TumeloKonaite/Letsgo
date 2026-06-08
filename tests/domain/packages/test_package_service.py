from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import pytest

from app.api.schemas.packages import PackageCreate, PackageUpdate
from app.domain.packages.repository import (
    PackageDetailRecord,
    PackageImageRecord,
    PackageListItemRecord,
    PackageRecord,
)
from app.domain.packages.service import (
    DuplicatePackageSlugError,
    PackageNotFoundError,
    PackageService,
)
from app.domain.packages.storage import StorageError
from app.infrastructure.database.models import PackagePublicationStatus
from app.infrastructure.packages.in_memory_package_repository import (
    InMemoryPackageRepository,
)


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


@dataclass
class FakeStorageService:
    def extract_object_name(self, url: str) -> str | None:
        prefix = "https://storage.googleapis.com/letsgosa-package-images/"
        if not url.startswith(prefix):
            return None
        return url[len(prefix) :]

    def get_public_url(self, object_name: str) -> str:
        return f"https://storage.googleapis.com/letsgosa-package-images/{object_name}"


@dataclass
class FailingStorageService(FakeStorageService):
    def get_public_url(self, object_name: str) -> str:
        raise StorageError("Storage backend unavailable")


@dataclass
class PublishedPackageRepository:
    list_item: PackageListItemRecord
    detail_item: PackageDetailRecord

    def list_all_packages(self) -> list[PackageRecord]:
        return []

    def create(self, package_data):
        raise NotImplementedError

    def get_by_id(self, package_id: int) -> PackageRecord | None:
        return None

    def get_by_slug(self, slug: str) -> PackageRecord | None:
        return None

    def update(self, package_id: int, package_data):
        return None

    def publish(self, package_id: int) -> PackageRecord | None:
        return None

    def unpublish(self, package_id: int) -> PackageRecord | None:
        return None

    def delete(self, package_id: int) -> bool:
        return False

    def list_published_packages(self) -> list[PackageListItemRecord]:
        return [self.list_item]

    def get_published_package_by_slug(self, slug: str) -> PackageDetailRecord | None:
        return self.detail_item if slug == self.detail_item.slug else None


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


def test_public_package_urls_are_normalized_for_storage_images() -> None:
    storage_image = PackageImageRecord(
        id=10,
        image_url="https://storage.googleapis.com/letsgosa-package-images/packages/cape-town/hero.jpg",
        alt_text="Hero",
        sort_order=0,
        is_cover=True,
    )
    repository = PublishedPackageRepository(
        list_item=PackageListItemRecord(
            id=1,
            slug="existing-package",
            title="Existing Package",
            short_description="Existing package.",
            location="Cape Town",
            duration_days=4,
            price_from=Decimal("4500.00"),
            currency="ZAR",
            is_featured=False,
            images=(storage_image,),
        ),
        detail_item=PackageDetailRecord(
            id=1,
            slug="existing-package",
            title="Existing Package",
            short_description="Existing package.",
            full_description="Existing package description.",
            location="Cape Town",
            duration_days=4,
            price_from=Decimal("4500.00"),
            currency="ZAR",
            is_featured=False,
            images=(storage_image,),
            itinerary=(),
            availability=(),
        ),
    )
    service = PackageService(
        repository=repository, storage_service=FakeStorageService()
    )

    list_payload = service.list_published_packages()
    detail_payload = service.get_published_package_by_slug("existing-package")

    assert list_payload[0].hero_image_url == (
        "https://storage.googleapis.com/letsgosa-package-images/packages/cape-town/hero.jpg"
    )
    assert detail_payload.hero_image_url == (
        "https://storage.googleapis.com/letsgosa-package-images/packages/cape-town/hero.jpg"
    )
    assert detail_payload.images[0].image_url == (
        "https://storage.googleapis.com/letsgosa-package-images/packages/cape-town/hero.jpg"
    )


def test_public_package_urls_fall_back_to_stored_url_when_storage_is_unavailable() -> (
    None
):
    storage_image = PackageImageRecord(
        id=10,
        image_url="https://storage.googleapis.com/letsgosa-package-images/packages/cape-town/hero.jpg",
        alt_text="Hero",
        sort_order=0,
        is_cover=True,
    )
    repository = PublishedPackageRepository(
        list_item=PackageListItemRecord(
            id=1,
            slug="existing-package",
            title="Existing Package",
            short_description="Existing package.",
            location="Cape Town",
            duration_days=4,
            price_from=Decimal("4500.00"),
            currency="ZAR",
            is_featured=False,
            images=(storage_image,),
        ),
        detail_item=PackageDetailRecord(
            id=1,
            slug="existing-package",
            title="Existing Package",
            short_description="Existing package.",
            full_description="Existing package description.",
            location="Cape Town",
            duration_days=4,
            price_from=Decimal("4500.00"),
            currency="ZAR",
            is_featured=False,
            images=(storage_image,),
            itinerary=(),
            availability=(),
        ),
    )
    service = PackageService(
        repository=repository, storage_service=FailingStorageService()
    )

    list_payload = service.list_published_packages()
    detail_payload = service.get_published_package_by_slug("existing-package")

    assert list_payload[0].hero_image_url == storage_image.image_url
    assert detail_payload.hero_image_url == storage_image.image_url
    assert detail_payload.images[0].image_url == storage_image.image_url
