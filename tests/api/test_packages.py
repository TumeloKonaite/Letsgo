from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
import pytest

from app.infrastructure.database.models import (
    Package,
    PackageAvailability,
    PackageAvailabilityStatus,
    PackageImage,
    PackageItineraryItem,
    PackagePublicationStatus,
)
from app.main import create_application
from tests.api.firebase_auth_helpers import build_test_settings


def seed_packages(session_factory) -> None:
    with session_factory() as session:
        featured_package = Package(
            title="Cape Town Explorer",
            slug="cape-town-explorer",
            short_description="Coastline, city, and wine country in one itinerary.",
            description="A four-day guided trip across Cape Town highlights.",
            destination="Cape Town",
            duration_days=4,
            duration_nights=3,
            price_from=Decimal("4999.00"),
            currency="ZAR",
            status=PackagePublicationStatus.PUBLISHED,
            is_featured=True,
            display_order=1,
        )
        featured_package.images.extend(
            [
                PackageImage(
                    image_url="https://example.com/gallery.jpg",
                    alt_text="Sunset over Camps Bay",
                    sort_order=2,
                    is_cover=False,
                ),
                PackageImage(
                    image_url="https://example.com/hero.jpg",
                    alt_text="Table Mountain at sunrise",
                    sort_order=10,
                    is_cover=True,
                ),
            ]
        )
        featured_package.itinerary_items.extend(
            [
                PackageItineraryItem(
                    day_number=2,
                    sort_order=1,
                    title="Peninsula tour",
                    description="Chapman's Peak and Cape Point.",
                ),
                PackageItineraryItem(
                    day_number=1,
                    sort_order=2,
                    title="Hotel check-in",
                    description="Arrival and waterfront evening.",
                ),
                PackageItineraryItem(
                    day_number=1,
                    sort_order=1,
                    title="Airport pickup",
                    description="Meet and transfer from the airport.",
                ),
            ]
        )
        featured_package.availability_dates.extend(
            [
                PackageAvailability(
                    start_date=date(2026, 11, 20),
                    end_date=date(2026, 11, 23),
                    capacity=16,
                    spots_available=4,
                    status=PackageAvailabilityStatus.SOLD_OUT,
                ),
                PackageAvailability(
                    start_date=date(2026, 10, 5),
                    end_date=date(2026, 10, 8),
                    capacity=16,
                    spots_available=10,
                    status=PackageAvailabilityStatus.AVAILABLE,
                ),
            ]
        )

        boolean_published_package = Package(
            title="Kruger Weekend Safari",
            slug="kruger-weekend-safari",
            short_description="Two nights focused on wildlife viewing.",
            description="A short safari break with game drives and lodge stay.",
            destination="Mpumalanga",
            duration_days=3,
            duration_nights=2,
            price_from=Decimal("5299.00"),
            currency="ZAR",
            status=PackagePublicationStatus.DRAFT,
            is_published=True,
            is_featured=False,
            display_order=2,
        )
        boolean_published_package.images.append(
            PackageImage(
                image_url="https://example.com/kruger.jpg",
                alt_text="Elephants at a waterhole",
                sort_order=0,
                is_cover=True,
            )
        )

        unpublished_package = Package(
            title="Hidden Retreat",
            slug="hidden-retreat",
            short_description="Private reserve stay.",
            description="An unpublished package for internal drafting only.",
            destination="Limpopo",
            duration_days=2,
            duration_nights=1,
            price_from=Decimal("3999.00"),
            currency="ZAR",
            status=PackagePublicationStatus.DRAFT,
            is_published=False,
            is_featured=False,
            display_order=99,
        )

        session.add_all(
            [featured_package, boolean_published_package, unpublished_package]
        )
        session.commit()


@pytest.fixture
def package_client(tmp_path) -> TestClient:
    database_url = f"sqlite:///{tmp_path / 'packages.db'}"
    application = create_application(settings=build_test_settings(database_url))

    with TestClient(application) as client:
        seed_packages(application.state.db_session_factory)
        yield client


def test_listing_published_packages(package_client: TestClient) -> None:
    response = package_client.get("/api/packages")

    assert response.status_code == 200
    payload = response.json()

    assert [item["slug"] for item in payload] == [
        "cape-town-explorer",
        "kruger-weekend-safari",
    ]
    assert payload[0]["title"] == "Cape Town Explorer"
    assert payload[0]["price_from"] == "4999.00"
    assert payload[0]["hero_image_url"] == "https://example.com/hero.jpg"
    assert payload[0]["is_featured"] is True


def test_listing_excludes_unpublished_packages(package_client: TestClient) -> None:
    response = package_client.get("/api/packages")

    assert response.status_code == 200
    assert {item["slug"] for item in response.json()} == {
        "cape-town-explorer",
        "kruger-weekend-safari",
    }


def test_fetching_package_details_by_slug(package_client: TestClient) -> None:
    response = package_client.get("/api/packages/cape-town-explorer")

    assert response.status_code == 200
    payload = response.json()

    assert payload["slug"] == "cape-town-explorer"
    assert (
        payload["full_description"]
        == "A four-day guided trip across Cape Town highlights."
    )
    assert payload["images"][0]["image_url"] == "https://example.com/hero.jpg"
    assert payload["hero_image_url"] == "https://example.com/hero.jpg"


def test_unknown_slug_returns_404(package_client: TestClient) -> None:
    response = package_client.get("/api/packages/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {"detail": "Package not found"}


def test_unpublished_slug_returns_404(package_client: TestClient) -> None:
    response = package_client.get("/api/packages/hidden-retreat")

    assert response.status_code == 404
    assert response.json() == {"detail": "Package not found"}


def test_itinerary_items_are_ordered_correctly(package_client: TestClient) -> None:
    response = package_client.get("/api/packages/cape-town-explorer")

    assert response.status_code == 200
    itinerary = response.json()["itinerary"]

    assert [
        (item["day_number"], item["sort_order"], item["title"]) for item in itinerary
    ] == [
        (1, 1, "Airport pickup"),
        (1, 2, "Hotel check-in"),
        (2, 1, "Peninsula tour"),
    ]


def test_availability_is_ordered_by_start_date(package_client: TestClient) -> None:
    response = package_client.get("/api/packages/cape-town-explorer")

    assert response.status_code == 200
    availability = response.json()["availability"]

    assert [item["start_date"] for item in availability] == [
        "2026-10-05",
        "2026-11-20",
    ]
