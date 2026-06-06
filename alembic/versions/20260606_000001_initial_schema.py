"""Create LetsGoSA application tables.

Revision ID: 20260606_000001
Revises:
Create Date: 2026-06-06 02:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260606_000001"
down_revision = None
branch_labels = None
depends_on = None

package_publication_status = sa.Enum(
    "draft",
    "published",
    "archived",
    name="package_publication_status",
    native_enum=False,
    create_constraint=True,
)

package_availability_status = sa.Enum(
    "available",
    "sold_out",
    "cancelled",
    "closed",
    name="package_availability_status",
    native_enum=False,
    create_constraint=True,
)

booking_status = sa.Enum(
    "new",
    "contacted",
    "confirmed",
    "cancelled",
    "closed",
    name="booking_status",
    native_enum=False,
    create_constraint=True,
)


def upgrade() -> None:
    op.create_table(
        "packages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("short_description", sa.String(length=500), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("destination", sa.String(length=150), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("duration_nights", sa.Integer(), nullable=False),
        sa.Column("price_from", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("status", package_publication_status, nullable=False, server_default="draft"),
        sa.Column(
            "is_published",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "is_featured",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "display_order >= 0",
            name=op.f("ck_packages_display_order_non_negative"),
        ),
        sa.CheckConstraint(
            "duration_days > 0",
            name=op.f("ck_packages_duration_days_positive"),
        ),
        sa.CheckConstraint(
            "duration_nights >= 0",
            name=op.f("ck_packages_duration_nights_non_negative"),
        ),
        sa.CheckConstraint(
            "price_from >= 0",
            name=op.f("ck_packages_price_from_non_negative"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_packages")),
    )
    op.create_index(op.f("ix_packages_destination"), "packages", ["destination"], unique=False)
    op.create_index(op.f("ix_packages_is_featured"), "packages", ["is_featured"], unique=False)
    op.create_index(
        op.f("ix_packages_is_published"),
        "packages",
        ["is_published"],
        unique=False,
    )
    op.create_index(op.f("ix_packages_slug"), "packages", ["slug"], unique=True)
    op.create_index(op.f("ix_packages_status"), "packages", ["status"], unique=False)

    op.create_table(
        "package_images",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("package_id", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(length=1024), nullable=True),
        sa.Column("image_url", sa.String(length=2048), nullable=False),
        sa.Column("alt_text", sa.String(length=255), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "is_cover",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "sort_order >= 0",
            name=op.f("ck_package_images_sort_order_non_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["package_id"],
            ["packages.id"],
            name=op.f("fk_package_images_package_id_packages"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_package_images")),
    )
    op.create_index(op.f("ix_package_images_package_id"), "package_images", ["package_id"], unique=False)
    op.create_index(
        "ix_package_images_package_id_sort_order",
        "package_images",
        ["package_id", "sort_order"],
        unique=False,
    )

    op.create_table(
        "package_itinerary_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("package_id", sa.Integer(), nullable=False),
        sa.Column("day_number", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "day_number > 0",
            name=op.f("ck_package_itinerary_items_day_number_positive"),
        ),
        sa.CheckConstraint(
            "sort_order >= 0",
            name=op.f("ck_package_itinerary_items_sort_order_non_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["package_id"],
            ["packages.id"],
            name=op.f("fk_package_itinerary_items_package_id_packages"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_package_itinerary_items")),
        sa.UniqueConstraint(
            "package_id",
            "day_number",
            "sort_order",
            name=op.f("uq_package_itinerary_items_package_day_sort"),
        ),
    )
    op.create_index(
        op.f("ix_package_itinerary_items_package_id"),
        "package_itinerary_items",
        ["package_id"],
        unique=False,
    )

    op.create_table(
        "package_availability",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("package_id", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("spots_available", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            package_availability_status,
            nullable=False,
            server_default="available",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "capacity > 0",
            name=op.f("ck_package_availability_capacity_positive"),
        ),
        sa.CheckConstraint(
            "end_date >= start_date",
            name=op.f("ck_package_availability_date_range_valid"),
        ),
        sa.CheckConstraint(
            "spots_available <= capacity",
            name=op.f("ck_package_availability_spots_available_within_capacity"),
        ),
        sa.CheckConstraint(
            "spots_available >= 0",
            name=op.f("ck_package_availability_spots_available_non_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["package_id"],
            ["packages.id"],
            name=op.f("fk_package_availability_package_id_packages"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_package_availability")),
    )
    op.create_index(
        "ix_package_availability_package_id_start_date",
        "package_availability",
        ["package_id", "start_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_package_availability_package_id"),
        "package_availability",
        ["package_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_package_availability_status"),
        "package_availability",
        ["status"],
        unique=False,
    )

    op.create_table(
        "bookings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("package_id", sa.Integer(), nullable=False),
        sa.Column("availability_id", sa.Integer(), nullable=True),
        sa.Column("customer_name", sa.String(length=255), nullable=False),
        sa.Column("customer_email", sa.String(length=320), nullable=False),
        sa.Column("customer_phone", sa.String(length=50), nullable=False),
        sa.Column("number_of_people", sa.Integer(), nullable=False),
        sa.Column("special_requests", sa.Text(), nullable=True),
        sa.Column("status", booking_status, nullable=False, server_default="new"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["availability_id"],
            ["package_availability.id"],
            name=op.f("fk_bookings_availability_id_package_availability"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["package_id"],
            ["packages.id"],
            name=op.f("fk_bookings_package_id_packages"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bookings")),
    )
    op.create_index(
        "ix_bookings_package_id_status",
        "bookings",
        ["package_id", "status"],
        unique=False,
    )
    op.create_index(op.f("ix_bookings_availability_id"), "bookings", ["availability_id"], unique=False)
    op.create_index(op.f("ix_bookings_package_id"), "bookings", ["package_id"], unique=False)
    op.create_index(op.f("ix_bookings_status"), "bookings", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_bookings_status"), table_name="bookings")
    op.drop_index(op.f("ix_bookings_package_id"), table_name="bookings")
    op.drop_index(op.f("ix_bookings_availability_id"), table_name="bookings")
    op.drop_index("ix_bookings_package_id_status", table_name="bookings")
    op.drop_table("bookings")

    op.drop_index(op.f("ix_package_availability_status"), table_name="package_availability")
    op.drop_index(op.f("ix_package_availability_package_id"), table_name="package_availability")
    op.drop_index(
        "ix_package_availability_package_id_start_date",
        table_name="package_availability",
    )
    op.drop_table("package_availability")

    op.drop_index(
        op.f("ix_package_itinerary_items_package_id"),
        table_name="package_itinerary_items",
    )
    op.drop_table("package_itinerary_items")

    op.drop_index(
        "ix_package_images_package_id_sort_order",
        table_name="package_images",
    )
    op.drop_index(op.f("ix_package_images_package_id"), table_name="package_images")
    op.drop_table("package_images")

    op.drop_index(op.f("ix_packages_status"), table_name="packages")
    op.drop_index(op.f("ix_packages_slug"), table_name="packages")
    op.drop_index(op.f("ix_packages_is_published"), table_name="packages")
    op.drop_index(op.f("ix_packages_is_featured"), table_name="packages")
    op.drop_index(op.f("ix_packages_destination"), table_name="packages")
    op.drop_table("packages")
