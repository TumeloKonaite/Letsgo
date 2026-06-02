from __future__ import annotations

from decimal import Decimal

import pytest

from app.domain.packages.repository import PackageCreateData
from app.infrastructure.database.models import PackagePublicationStatus
from app.infrastructure.database.session import (
    create_database_engine,
    create_session_factory,
    initialize_database,
)
from app.infrastructure.packages.postgres_package_repository import PostgresPackageRepository


@pytest.fixture
def package_repository(tmp_path) -> PostgresPackageRepository:
    database_url = f"sqlite:///{tmp_path / 'repository.db'}"
    engine = create_database_engine(database_url)
    initialize_database(engine)
    session_factory = create_session_factory(engine)
    repository = PostgresPackageRepository(session_factory=session_factory)

    try:
        yield repository
    finally:
        engine.dispose()


def _create_package(repository: PostgresPackageRepository):
    return repository.create(
        PackageCreateData(
            title="Repository Package",
            slug="repository-package",
            short_description="Repository test package.",
            description="Repository-backed package description.",
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
    )


def test_create_and_get_by_id(package_repository: PostgresPackageRepository) -> None:
    created_package = _create_package(package_repository)

    loaded_package = package_repository.get_by_id(created_package.id)

    assert loaded_package is not None
    assert loaded_package.slug == "repository-package"


def test_get_by_slug(package_repository: PostgresPackageRepository) -> None:
    _create_package(package_repository)

    package = package_repository.get_by_slug("repository-package")

    assert package is not None
    assert package.title == "Repository Package"


def test_update_package(package_repository: PostgresPackageRepository) -> None:
    created_package = _create_package(package_repository)

    updated_package = package_repository.update(
        created_package.id,
        {
            "title": "Updated Repository Package",
            "price_from": Decimal("4999.00"),
        },
    )

    assert updated_package is not None
    assert updated_package.title == "Updated Repository Package"
    assert updated_package.price_from == Decimal("4999.00")


def test_publish_package(package_repository: PostgresPackageRepository) -> None:
    created_package = _create_package(package_repository)

    published_package = package_repository.publish(created_package.id)

    assert published_package is not None
    assert published_package.status == PackagePublicationStatus.PUBLISHED
    assert published_package.is_published is True


def test_unpublish_package(package_repository: PostgresPackageRepository) -> None:
    created_package = _create_package(package_repository)
    package_repository.publish(created_package.id)

    unpublished_package = package_repository.unpublish(created_package.id)

    assert unpublished_package is not None
    assert unpublished_package.status == PackagePublicationStatus.DRAFT
    assert unpublished_package.is_published is False


def test_delete_package(package_repository: PostgresPackageRepository) -> None:
    created_package = _create_package(package_repository)

    deleted = package_repository.delete(created_package.id)

    assert deleted is True
    assert package_repository.get_by_id(created_package.id) is None


def test_delete_missing_package_returns_false(package_repository: PostgresPackageRepository) -> None:
    assert package_repository.delete(999) is False
