"""Create contact submissions table.

Revision ID: 20260608_000002
Revises: 20260606_000001
Create Date: 2026-06-08 14:30:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260608_000002"
down_revision = "20260606_000001"
branch_labels = None
depends_on = None

contact_email_status = sa.Enum(
    "pending",
    "sent",
    "failed",
    name="contact_email_status",
    native_enum=False,
    create_constraint=True,
)


def upgrade() -> None:
    op.create_table(
        "contact_submissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("subject", sa.String(length=200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "email_status",
            contact_email_status,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("email_error", sa.Text(), nullable=True),
        sa.Column("emailed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_contact_submissions")),
    )
    op.create_index(
        op.f("ix_contact_submissions_email_status"),
        "contact_submissions",
        ["email_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_contact_submissions_email_status"),
        table_name="contact_submissions",
    )
    op.drop_table("contact_submissions")
