from __future__ import annotations

from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.database.models import Base

REQUIRED_TABLES = frozenset(
    {
        "packages",
        "package_images",
        "package_itinerary_items",
        "package_availability",
        "bookings",
    }
)


def create_database_engine(database_url: str) -> Engine:
    connect_args: dict[str, bool] = {}
    engine_kwargs: dict[str, object] = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    else:
        # Cloud SQL connections can stay in the pool across instance reuse, so
        # pre-ping each checkout to fail fast on stale connections.
        engine_kwargs["pool_pre_ping"] = True

    return create_engine(database_url, connect_args=connect_args, **engine_kwargs)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )


def initialize_database(engine: Engine) -> None:
    if engine.dialect.name == "sqlite":
        Base.metadata.create_all(engine)
        _ensure_package_image_storage_key_column(engine)
        _migrate_legacy_package_statuses(engine)
        _migrate_legacy_booking_statuses(engine)
        return

    _verify_database_connection(engine)
    _verify_required_tables(engine)


def _verify_database_connection(engine: Engine) -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))


def verify_session_connection(session: Session) -> None:
    session.execute(text("SELECT 1"))


def _verify_required_tables(engine: Engine) -> None:
    existing_tables = set(inspect(engine).get_table_names())
    missing_tables = sorted(REQUIRED_TABLES - existing_tables)
    if not missing_tables:
        return

    missing = ", ".join(missing_tables)
    raise RuntimeError(
        "Database schema is missing required tables. "
        "Run `alembic upgrade head` before starting the application. "
        f"Missing tables: {missing}"
    )


def _ensure_package_image_storage_key_column(engine: Engine) -> None:
    inspector = inspect(engine)
    if "package_images" not in inspector.get_table_names():
        return

    existing_columns = {
        column["name"] for column in inspector.get_columns("package_images")
    }
    if "storage_key" in existing_columns:
        return

    with engine.begin() as connection:
        connection.execute(
            text("ALTER TABLE package_images ADD COLUMN storage_key VARCHAR(1024)")
        )


def _migrate_legacy_booking_statuses(engine: Engine) -> None:
    inspector = inspect(engine)
    if "bookings" not in inspector.get_table_names():
        return

    with engine.begin() as connection:
        connection.execute(
            text("UPDATE bookings SET status = 'new' WHERE status = 'pending'")
        )
        connection.execute(
            text("UPDATE bookings SET status = 'closed' WHERE status = 'rejected'")
        )


def _migrate_legacy_package_statuses(engine: Engine) -> None:
    inspector = inspect(engine)
    if "packages" not in inspector.get_table_names():
        return

    with engine.begin() as connection:
        connection.execute(
            text("UPDATE packages SET status = 'draft' WHERE status = 'DRAFT'")
        )
        connection.execute(
            text("UPDATE packages SET status = 'published' WHERE status = 'PUBLISHED'")
        )
        connection.execute(
            text("UPDATE packages SET status = 'archived' WHERE status = 'ARCHIVED'")
        )
