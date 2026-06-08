from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint
from sqlalchemy import create_engine, text
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.dialects import postgresql

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
from app.infrastructure.database.session import (
    REQUIRED_TABLES,
    create_database_engine,
    initialize_database,
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
    image = PackageImage(
        image_url="https://example.com/cover.jpg", alt_text="Table Mountain"
    )
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
        status=BookingStatus.NEW,
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


def test_create_database_engine_supports_postgresql_psycopg_urls() -> None:
    engine = create_database_engine(
        "postgresql+psycopg://user:password@db.example.com:5432/letsgosa_prod"
    )

    try:
        assert engine.dialect.name == "postgresql"
        assert engine.url.drivername == "postgresql+psycopg"
    finally:
        engine.dispose()


def test_create_database_engine_supports_cloud_sql_unix_socket_urls() -> None:
    engine = create_database_engine(
        "postgresql+psycopg://letsgodev:password@/letsgo"
        "?host=/cloudsql/letsgodb:us-central1:free-trial-first-project"
    )

    try:
        assert engine.dialect.name == "postgresql"
        assert engine.url.drivername == "postgresql+psycopg"
        assert (
            engine.url.query["host"]
            == "/cloudsql/letsgodb:us-central1:free-trial-first-project"
        )
    finally:
        engine.dispose()


def test_package_publication_status_persists_lowercase_values_for_postgresql() -> None:
    bind_processor = Package.__table__.c.status.type.bind_processor(
        postgresql.dialect()
    )

    assert bind_processor is not None
    assert bind_processor(PackagePublicationStatus.DRAFT) == "draft"


def test_booking_status_persists_lowercase_values_for_postgresql() -> None:
    bind_processor = Booking.__table__.c.status.type.bind_processor(
        postgresql.dialect()
    )

    assert bind_processor is not None
    assert bind_processor(BookingStatus.NEW) == "new"


def test_initialize_database_creates_expected_tables_for_sqlite(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'schema.db'}")

    try:
        initialize_database(engine)

        table_names = set(sa_inspect(engine).get_table_names())
        assert REQUIRED_TABLES.issubset(table_names)
    finally:
        engine.dispose()


def test_initialize_database_adds_storage_key_column_for_existing_tables(
    tmp_path,
) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE package_images (
                    id INTEGER PRIMARY KEY,
                    package_id INTEGER NOT NULL,
                    image_url VARCHAR(2048) NOT NULL,
                    alt_text VARCHAR(255),
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    is_cover BOOLEAN NOT NULL DEFAULT 0,
                    created_at DATETIME
                )
                """
            )
        )

    try:
        initialize_database(engine)

        columns = {
            column["name"]
            for column in sa_inspect(engine).get_columns("package_images")
        }

        assert "storage_key" in columns
    finally:
        engine.dispose()


def test_initialize_database_migrates_legacy_booking_status_values(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy-bookings.db'}")

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE bookings (
                    id INTEGER PRIMARY KEY,
                    package_id INTEGER NOT NULL,
                    availability_id INTEGER,
                    customer_name VARCHAR(255) NOT NULL,
                    customer_email VARCHAR(320) NOT NULL,
                    customer_phone VARCHAR(50) NOT NULL,
                    number_of_people INTEGER NOT NULL,
                    special_requests TEXT,
                    status VARCHAR(50) NOT NULL,
                    created_at DATETIME,
                    updated_at DATETIME
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO bookings (
                    package_id,
                    availability_id,
                    customer_name,
                    customer_email,
                    customer_phone,
                    number_of_people,
                    special_requests,
                    status
                ) VALUES
                    (1, NULL, 'Legacy Pending', 'pending@example.com', '+27 11 000 0000', 2, NULL, 'pending'),
                    (1, NULL, 'Legacy Rejected', 'rejected@example.com', '+27 11 000 0001', 1, NULL, 'rejected')
                """
            )
        )

    try:
        initialize_database(engine)

        with engine.connect() as connection:
            rows = (
                connection.execute(text("SELECT status FROM bookings ORDER BY id ASC"))
                .scalars()
                .all()
            )

        assert rows == ["new", "closed"]
    finally:
        engine.dispose()


def test_initialize_database_migrates_legacy_package_status_values(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy-packages.db'}")

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE packages (
                    id INTEGER PRIMARY KEY,
                    title VARCHAR(200) NOT NULL,
                    slug VARCHAR(255) NOT NULL,
                    short_description VARCHAR(500),
                    description TEXT NOT NULL,
                    destination VARCHAR(150) NOT NULL,
                    duration_days INTEGER NOT NULL,
                    duration_nights INTEGER NOT NULL,
                    price_from NUMERIC(10, 2) NOT NULL,
                    currency VARCHAR(3) NOT NULL,
                    is_active BOOLEAN NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    is_published BOOLEAN NOT NULL,
                    is_featured BOOLEAN NOT NULL,
                    display_order INTEGER NOT NULL,
                    created_at DATETIME,
                    updated_at DATETIME
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO packages (
                    title,
                    slug,
                    short_description,
                    description,
                    destination,
                    duration_days,
                    duration_nights,
                    price_from,
                    currency,
                    is_active,
                    status,
                    is_published,
                    is_featured,
                    display_order
                ) VALUES
                    ('Legacy Draft', 'legacy-draft', NULL, 'Draft package', 'Cape Town', 3, 2, 1000, 'ZAR', 1, 'DRAFT', 0, 0, 0),
                    ('Legacy Published', 'legacy-published', NULL, 'Published package', 'Johannesburg', 4, 3, 2000, 'ZAR', 1, 'PUBLISHED', 1, 0, 1),
                    ('Legacy Archived', 'legacy-archived', NULL, 'Archived package', 'Durban', 5, 4, 3000, 'ZAR', 0, 'ARCHIVED', 0, 0, 2)
                """
            )
        )

    try:
        initialize_database(engine)

        with engine.connect() as connection:
            rows = (
                connection.execute(text("SELECT status FROM packages ORDER BY id ASC"))
                .scalars()
                .all()
            )

        assert rows == ["draft", "published", "archived"]
    finally:
        engine.dispose()
