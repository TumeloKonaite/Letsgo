from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    Enum as SqlEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.models.base import Base, CreatedAtMixin, TimestampMixin


def _enum_values(enum_cls: type[Enum]) -> list[str]:
    return [member.value for member in enum_cls]


class PackageAvailabilityStatus(str, Enum):
    AVAILABLE = "available"
    SOLD_OUT = "sold_out"
    CANCELLED = "cancelled"
    CLOSED = "closed"


class PackagePublicationStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class Package(TimestampMixin, Base):
    __tablename__ = "packages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    short_description: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    destination: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_nights: Mapped[int] = mapped_column(Integer, nullable=False)
    price_from: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="ZAR")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[PackagePublicationStatus] = mapped_column(
        SqlEnum(
            PackagePublicationStatus,
            name="package_publication_status",
            native_enum=False,
            validate_strings=True,
            values_callable=_enum_values,
        ),
        nullable=False,
        default=PackagePublicationStatus.DRAFT,
        index=True,
    )
    is_published: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    is_featured: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    images: Mapped[list[PackageImage]] = relationship(
        back_populates="package",
        cascade="all, delete-orphan",
        order_by=lambda: [
            PackageImage.is_cover.desc(),
            PackageImage.sort_order.asc(),
            PackageImage.id.asc(),
        ],
    )
    itinerary_items: Mapped[list[PackageItineraryItem]] = relationship(
        back_populates="package",
        cascade="all, delete-orphan",
        order_by=lambda: [
            PackageItineraryItem.day_number.asc(),
            PackageItineraryItem.sort_order.asc(),
            PackageItineraryItem.id.asc(),
        ],
    )
    availability_dates: Mapped[list[PackageAvailability]] = relationship(
        back_populates="package",
        cascade="all, delete-orphan",
        order_by=lambda: [
            PackageAvailability.start_date.asc(),
            PackageAvailability.id.asc(),
        ],
    )
    bookings: Mapped[list[Booking]] = relationship(
        back_populates="package",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint("duration_days > 0", name="duration_days_positive"),
        CheckConstraint("duration_nights >= 0", name="duration_nights_non_negative"),
        CheckConstraint("price_from >= 0", name="price_from_non_negative"),
        CheckConstraint("display_order >= 0", name="display_order_non_negative"),
    )


class PackageImage(CreatedAtMixin, Base):
    __tablename__ = "package_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    package_id: Mapped[int] = mapped_column(
        ForeignKey("packages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    storage_key: Mapped[str | None] = mapped_column(String(1024))
    image_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    alt_text: Mapped[str | None] = mapped_column(String(255))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_cover: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    package: Mapped[Package] = relationship(back_populates="images")

    __table_args__ = (
        CheckConstraint("sort_order >= 0", name="sort_order_non_negative"),
        Index("ix_package_images_package_id_sort_order", "package_id", "sort_order"),
    )


class PackageItineraryItem(CreatedAtMixin, Base):
    __tablename__ = "package_itinerary_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    package_id: Mapped[int] = mapped_column(
        ForeignKey("packages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    package: Mapped[Package] = relationship(back_populates="itinerary_items")

    __table_args__ = (
        CheckConstraint("day_number > 0", name="day_number_positive"),
        CheckConstraint("sort_order >= 0", name="sort_order_non_negative"),
        UniqueConstraint(
            "package_id",
            "day_number",
            "sort_order",
            name="uq_package_itinerary_items_package_day_sort",
        ),
    )


class PackageAvailability(TimestampMixin, Base):
    __tablename__ = "package_availability"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    package_id: Mapped[int] = mapped_column(
        ForeignKey("packages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    spots_available: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[PackageAvailabilityStatus] = mapped_column(
        SqlEnum(
            PackageAvailabilityStatus,
            name="package_availability_status",
            native_enum=False,
            validate_strings=True,
            values_callable=_enum_values,
        ),
        nullable=False,
        default=PackageAvailabilityStatus.AVAILABLE,
        index=True,
    )

    package: Mapped[Package] = relationship(back_populates="availability_dates")
    bookings: Mapped[list[Booking]] = relationship(back_populates="availability")

    __table_args__ = (
        CheckConstraint("capacity > 0", name="capacity_positive"),
        CheckConstraint("spots_available >= 0", name="spots_available_non_negative"),
        CheckConstraint(
            "spots_available <= capacity", name="spots_available_within_capacity"
        ),
        CheckConstraint("end_date >= start_date", name="date_range_valid"),
        Index(
            "ix_package_availability_package_id_start_date", "package_id", "start_date"
        ),
    )


from app.infrastructure.database.models.booking import Booking
