"""Define the email delivery contract and errors handled by the contact service."""

from __future__ import annotations

from typing import Protocol

from app.domain.contact.models import ContactSubmission


class EmailDeliveryError(Exception):
    """Raised when an outbound contact email cannot be delivered."""


class EmailSender(Protocol):
    def send_contact_request(self, submission: ContactSubmission) -> None:
        """Send a contact notification email."""
