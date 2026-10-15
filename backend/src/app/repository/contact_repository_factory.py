"""Select the configured contact repository implementation."""

from sqlalchemy.orm import Session, sessionmaker

from app.repository.null_contact_repository import NullContactRepository
from app.repository.postgres_contact_repository import PostgresContactRepository
from app.services.contact.ports import ContactRepository


def build_contact_repository(
    *,
    session_factory: sessionmaker[Session] | None,
) -> ContactRepository:
    if session_factory is None:
        return NullContactRepository()
    return PostgresContactRepository(session_factory=session_factory)
