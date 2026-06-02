from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint
from sqlalchemy import inspect as sa_inspect

from app.infrastructure.database.models import (
    Base,
    Booking,
    BookingStatus,
    Package,
    PackageAvailability,
    PackageAvailabilityStatus,
    PackageImage,
    PackageItineraryItem,
    PackagePublicationStatus,
)


def test_models_are_importable_and_registered() -> None:
    assert Package.__tablename__ == "packages"
    assert Booking.__tablename__ == "bookings"
    assert {
        "packages",
        "package_images",
        "package_itinerary_items",
        "package_availability",
        "bookings",
    }.issubset(Base.metadata.tables.keys())
    assert PackagePublicationStatus.PUBLISHED.value == "published"


def test_package_relationships_are_wired_correctly() -> None:
    package = Package(
        title="Cape Town Explorer",
        slug="cape-town-explorer",
        short_description="A coastal getaway.",
        description="Explore Cape Town across city, coast, and wine routes.",
        destination="Cape Town",
        duration_days=4,
        duration_nights=3,
        price_from=Decimal("4999.00"),
        currency="ZAR",
    )
    image = PackageImage(image_url="https://example.com/cover.jpg", alt_text="Table Mountain")
    itinerary = PackageItineraryItem(
        day_number=1,
        sort_order=0,
        title="Arrival",
        description="Airport pickup and hotel check-in.",
    )
    availability = PackageAvailability(
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 4),
        capacity=20,
        spots_available=8,
        status=PackageAvailabilityStatus.AVAILABLE,
    )

    package.images.append(image)
    package.itinerary_items.append(itinerary)
    package.availability_dates.append(availability)

    assert image.package is package
    assert itinerary.package is package
    assert availability.package is package
    assert package.images == [image]
    assert package.itinerary_items == [itinerary]
    assert package.availability_dates == [availability]

    relationships = sa_inspect(Package).relationships
    assert relationships["images"].mapper.class_ is PackageImage
    assert relationships["itinerary_items"].mapper.class_ is PackageItineraryItem
    assert relationships["availability_dates"].mapper.class_ is PackageAvailability


def test_booking_references_package_and_optional_availability() -> None:
    package = Package(
        title="Garden Route Escape",
        slug="garden-route-escape",
        short_description="A scenic road trip.",
        description="Drive the Garden Route with guided stops and stays.",
        destination="Garden Route",
        duration_days=5,
        duration_nights=4,
        price_from=Decimal("6499.00"),
        currency="ZAR",
    )
    availability = PackageAvailability(
        start_date=date(2026, 10, 10),
        end_date=date(2026, 10, 14),
        capacity=16,
        spots_available=12,
        status=PackageAvailabilityStatus.AVAILABLE,
    )
    booking = Booking(
        customer_name="Jordan Example",
        customer_email="jordan@example.com",
        customer_phone="+27 82 000 0000",
        number_of_people=2,
        special_requests="Vegetarian meals",
        status=BookingStatus.PENDING,
    )

    package.availability_dates.append(availability)
    package.bookings.append(booking)
    booking.availability = availability

    assert booking.package is package
    assert booking.availability is availability
    assert booking in package.bookings
    assert booking in availability.bookings


def test_availability_constraints_cover_capacity_and_spots() -> None:
    constraints = {
        str(constraint.sqltext)
        for constraint in PackageAvailability.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert "capacity > 0" in constraints
    assert "spots_available >= 0" in constraints
    assert "spots_available <= capacity" in constraints


def test_package_constraints_cover_public_display_ordering() -> None:
    constraints = {
        str(constraint.sqltext)
        for constraint in Package.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    itinerary_constraints = {
        str(constraint.sqltext)
        for constraint in PackageItineraryItem.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert "display_order >= 0" in constraints
    assert "sort_order >= 0" in itinerary_constraints
