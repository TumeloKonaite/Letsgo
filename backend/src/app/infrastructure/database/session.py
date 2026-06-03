from __future__ import annotations

from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.database.models import Base


def create_database_engine(database_url: str) -> Engine:
    connect_args: dict[str, bool] = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    return create_engine(database_url, connect_args=connect_args)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def initialize_database(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    _ensure_package_image_storage_key_column(engine)
    _migrate_legacy_booking_statuses(engine)


def _ensure_package_image_storage_key_column(engine: Engine) -> None:
    inspector = inspect(engine)
    if "package_images" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("package_images")}
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
        connection.execute(text("UPDATE bookings SET status = 'new' WHERE status = 'pending'"))
        connection.execute(text("UPDATE bookings SET status = 'closed' WHERE status = 'rejected'"))
