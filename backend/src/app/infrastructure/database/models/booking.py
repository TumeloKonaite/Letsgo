from __future__ import annotations

from enum import Enum

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.models.base import Base, TimestampMixin


class BookingStatus(str, Enum):
    NEW = "new"
    CONTACTED = "contacted"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    CLOSED = "closed"


class Booking(TimestampMixin, Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    package_id: Mapped[int] = mapped_column(
        ForeignKey("packages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    availability_id: Mapped[int | None] = mapped_column(
        ForeignKey("package_availability.id", ondelete="SET NULL"),
        index=True,
    )
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_email: Mapped[str] = mapped_column(String(320), nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(50), nullable=False)
    number_of_people: Mapped[int] = mapped_column(Integer, nullable=False)
    special_requests: Mapped[str | None] = mapped_column(Text)
    status: Mapped[BookingStatus] = mapped_column(
        SqlEnum(
            BookingStatus,
            name="booking_status",
            native_enum=False,
            validate_strings=True,
        ),
        nullable=False,
        default=BookingStatus.NEW,
        index=True,
    )

    package: Mapped[Package] = relationship(back_populates="bookings")
    availability: Mapped[PackageAvailability | None] = relationship(back_populates="bookings")

    __table_args__ = (
        Index("ix_bookings_package_id_status", "package_id", "status"),
    )


from app.infrastructure.database.models.package import Package, PackageAvailability
