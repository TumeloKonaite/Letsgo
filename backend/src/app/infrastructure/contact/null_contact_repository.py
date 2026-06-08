from __future__ import annotations

from app.domain.contact.models import ContactSubmission


class NullContactRepository:
    """Fallback repository used when database persistence is unavailable."""

    def __init__(self) -> None:
        self._next_submission_id = 1

    def create(self, submission: ContactSubmission) -> int:
        submission_id = self._next_submission_id
        self._next_submission_id += 1
        return submission_id

    def mark_email_sent(self, submission_id: int) -> None:
        return None

    def mark_email_failed(
        self,
        submission_id: int,
        error_message: str | None = None,
    ) -> None:
        return None
