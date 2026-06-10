"""Add structured package itinerary and inclusion content.

Revision ID: 20260610_000003
Revises: 20260608_000002
Create Date: 2026-06-10 12:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260610_000003"
down_revision = "20260608_000002"
branch_labels = None
depends_on = None

package_inclusion_type = sa.Enum(
    "included",
    "excluded",
    name="package_inclusion_type",
    native_enum=False,
    create_constraint=True,
)


def upgrade() -> None:
    bind = op.get_bind()
    package_inclusion_type.create(bind, checkfirst=True)

    with op.batch_alter_table("package_itinerary_items") as batch_op:
        batch_op.add_column(sa.Column("duration", sa.String(length=100), nullable=True))
        batch_op.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            )
        )
        batch_op.alter_column(
            "day_number",
            existing_type=sa.Integer(),
            server_default="1",
        )

    op.execute(
        sa.text(
            """
            UPDATE package_itinerary_items
            SET updated_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP)
            """
        )
    )
    op.execute(
        sa.text(
            """
            WITH ordered AS (
                SELECT
                    id,
                    ROW_NUMBER() OVER (
                        PARTITION BY package_id
                        ORDER BY day_number ASC, sort_order ASC, id ASC
                    ) - 1 AS next_sort_order
                FROM package_itinerary_items
            )
            UPDATE package_itinerary_items
            SET sort_order = ordered.next_sort_order
            FROM ordered
            WHERE ordered.id = package_itinerary_items.id
            """
        )
    )

    op.create_table(
        "package_inclusions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("package_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "type",
            package_inclusion_type,
            nullable=False,
            server_default="included",
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
            name=op.f("ck_package_inclusions_display_order_non_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["package_id"],
            ["packages.id"],
            name=op.f("fk_package_inclusions_package_id_packages"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_package_inclusions")),
    )
    op.create_index(
        op.f("ix_package_inclusions_package_id"),
        "package_inclusions",
        ["package_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_package_inclusions_type"),
        "package_inclusions",
        ["type"],
        unique=False,
    )
    op.create_index(
        "ix_package_inclusions_package_id_type_display_order",
        "package_inclusions",
        ["package_id", "type", "display_order"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_package_inclusions_package_id_type_display_order",
        table_name="package_inclusions",
    )
    op.drop_index(
        op.f("ix_package_inclusions_type"),
        table_name="package_inclusions",
    )
    op.drop_index(
        op.f("ix_package_inclusions_package_id"),
        table_name="package_inclusions",
    )
    op.drop_table("package_inclusions")

    with op.batch_alter_table("package_itinerary_items") as batch_op:
        batch_op.alter_column(
            "day_number",
            existing_type=sa.Integer(),
            server_default=None,
        )
        batch_op.drop_column("updated_at")
        batch_op.drop_column("duration")

    package_inclusion_type.drop(op.get_bind(), checkfirst=True)
