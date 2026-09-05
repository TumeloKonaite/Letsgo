"""Specify enquiry persistence and email delivery status tracking."""

from __future__ import annotations

from typing import Protocol

from app.domain.contact.models import ContactSubmission


class ContactRepository(Protocol):
    def create(self, submission: ContactSubmission) -> int:
        """Persist a new contact submission and return its identifier."""

    def mark_email_sent(self, submission_id: int) -> None:
        """Persist a successful email delivery for a contact submission."""

    def mark_email_failed(
        self,
        submission_id: int,
        error_message: str | None = None,
    ) -> None:
        """Persist a failed email delivery for a contact submission."""
