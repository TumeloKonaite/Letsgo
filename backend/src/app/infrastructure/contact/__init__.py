from sqlalchemy.orm import Session, sessionmaker

from app.domain.contact.repository import ContactRepository
from app.infrastructure.contact.null_contact_repository import NullContactRepository
from app.infrastructure.contact.postgres_contact_repository import (
    PostgresContactRepository,
)


def build_contact_repository(
    *,
    session_factory: sessionmaker[Session] | None,
) -> ContactRepository:
    if session_factory is None:
        return NullContactRepository()
    return PostgresContactRepository(session_factory=session_factory)


__all__ = [
    "NullContactRepository",
    "PostgresContactRepository",
    "build_contact_repository",
]
