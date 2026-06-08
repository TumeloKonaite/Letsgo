from __future__ import annotations

from pathlib import Path

from app.domain.contact import ContactSubmission
from app.infrastructure.contact import PostgresContactRepository
from app.infrastructure.database.models import Base, ContactEmailStatus
from app.infrastructure.database.models import (
    ContactSubmission as ContactSubmissionModel,
)
from app.infrastructure.database.session import (
    create_database_engine,
    create_session_factory,
)


def _build_repository(tmp_path: Path) -> tuple[PostgresContactRepository, object]:
    engine = create_database_engine(f"sqlite:///{tmp_path / 'contact_repository.db'}")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    return PostgresContactRepository(session_factory=session_factory), session_factory


def _contact_submission() -> ContactSubmission:
    return ContactSubmission(
        first_name="Jane",
        last_name="Doe",
        email="jane@example.com",
        phone="+27 82 123 4567",
        subject="Custom safari planning",
        message="I would like help planning a private guided trip in September.",
    )


def test_create_persists_contact_submission(tmp_path: Path) -> None:
    repository, session_factory = _build_repository(tmp_path)

    submission_id = repository.create(_contact_submission())

    with session_factory() as session:
        record = session.get(ContactSubmissionModel, submission_id)

    assert record is not None
    assert record.first_name == "Jane"
    assert record.last_name == "Doe"
    assert record.email == "jane@example.com"
    assert record.phone == "+27 82 123 4567"
    assert record.subject == "Custom safari planning"
    assert (
        record.message
        == "I would like help planning a private guided trip in September."
    )
    assert record.email_status == ContactEmailStatus.PENDING
    assert record.email_error is None
    assert record.emailed_at is None


def test_mark_email_sent_updates_delivery_fields(tmp_path: Path) -> None:
    repository, session_factory = _build_repository(tmp_path)
    submission_id = repository.create(_contact_submission())
    repository.mark_email_failed(submission_id, "transient smtp failure")

    repository.mark_email_sent(submission_id)

    with session_factory() as session:
        record = session.get(ContactSubmissionModel, submission_id)

    assert record is not None
    assert record.email_status == ContactEmailStatus.SENT
    assert record.emailed_at is not None
    assert record.email_error is None


def test_mark_email_failed_updates_delivery_fields(tmp_path: Path) -> None:
    repository, session_factory = _build_repository(tmp_path)
    submission_id = repository.create(_contact_submission())

    repository.mark_email_failed(submission_id, "smtp failure")

    with session_factory() as session:
        record = session.get(ContactSubmissionModel, submission_id)

    assert record is not None
    assert record.email_status == ContactEmailStatus.FAILED
    assert record.email_error == "smtp failure"
