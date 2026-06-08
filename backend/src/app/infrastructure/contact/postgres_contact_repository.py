from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session, sessionmaker

from app.domain.contact.models import ContactSubmission
from app.infrastructure.database.models import ContactSubmission as ContactSubmissionModel
from app.infrastructure.database.models import ContactEmailStatus


class PostgresContactRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create(self, submission: ContactSubmission) -> int:
        with self._session_factory.begin() as session:
            record = ContactSubmissionModel(
                first_name=submission.first_name,
                last_name=submission.last_name,
                email=submission.email,
                phone=submission.phone,
                subject=submission.subject,
                message=submission.message,
                email_status=ContactEmailStatus.PENDING,
            )
            session.add(record)
            session.flush()
            return record.id

    def mark_email_sent(self, submission_id: int) -> None:
        with self._session_factory.begin() as session:
            record = self._get_submission(session, submission_id)
            record.email_status = ContactEmailStatus.SENT
            record.emailed_at = datetime.now(UTC)
            record.email_error = None

    def mark_email_failed(
        self,
        submission_id: int,
        error_message: str | None = None,
    ) -> None:
        with self._session_factory.begin() as session:
            record = self._get_submission(session, submission_id)
            record.email_status = ContactEmailStatus.FAILED
            record.email_error = error_message

    def _get_submission(
        self,
        session: Session,
        submission_id: int,
    ) -> ContactSubmissionModel:
        record = session.get(ContactSubmissionModel, submission_id)
        if record is None:
            raise ValueError(f"Contact submission {submission_id} was not found.")
        return record
