from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.models.base import Base, CreatedAtMixin


def _enum_values(enum_cls: type[Enum]) -> list[str]:
    return [member.value for member in enum_cls]


class ContactEmailStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class ContactSubmission(CreatedAtMixin, Base):
    __tablename__ = "contact_submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    email_status: Mapped[ContactEmailStatus] = mapped_column(
        SqlEnum(
            ContactEmailStatus,
            name="contact_email_status",
            native_enum=False,
            validate_strings=True,
            values_callable=_enum_values,
        ),
        nullable=False,
        default=ContactEmailStatus.PENDING,
        index=True,
    )
    email_error: Mapped[str | None] = mapped_column(Text)
    emailed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
