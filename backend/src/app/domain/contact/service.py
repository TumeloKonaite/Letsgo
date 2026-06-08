from __future__ import annotations

from app.domain.contact.models import ContactSubmission
from app.domain.contact.repository import ContactRepository
from app.infrastructure.email.base import EmailDeliveryError, EmailSender


class ContactServiceError(Exception):
    """Raised when a contact request cannot be processed safely."""


class ContactService:
    def __init__(
        self,
        email_sender: EmailSender,
        repository: ContactRepository,
    ) -> None:
        self._email_sender = email_sender
        self._repository = repository

    def submit_contact_request(self, submission: ContactSubmission) -> None:
        try:
            submission_id = self._repository.create(submission)
        except Exception as exc:
            raise ContactServiceError("Unable to send contact request.") from exc

        try:
            self._email_sender.send_contact_request(submission)
        except EmailDeliveryError as exc:
            self._repository.mark_email_failed(submission_id, str(exc) or None)
            raise ContactServiceError("Unable to send contact request.") from exc

        try:
            self._repository.mark_email_sent(submission_id)
        except Exception as exc:
            raise ContactServiceError("Unable to send contact request.") from exc
