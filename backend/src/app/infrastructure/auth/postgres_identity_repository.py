"""Resolve and provision normalized users by trusted external subject."""

from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, sessionmaker

from app.domain.auth.models import AuthenticatedUser
from app.infrastructure.database.models.user import ApplicationUser, UserIdentity


class PostgresIdentityRepository:
    """Store local users without treating mutable profile fields as link keys."""

    def __init__(self, *, session_factory: sessionmaker) -> None:
        self._session_factory = session_factory

    def resolve_or_provision(self, user: AuthenticatedUser) -> AuthenticatedUser:
        with self._session_factory() as session:
            identity = session.scalar(self._identity_query(user))
            if identity is None:
                application_user = ApplicationUser(
                    id=str(uuid4()), username=user.username, email=user.email
                )
                identity = UserIdentity(
                    user=application_user,
                    provider=user.provider,
                    subject=user.subject,
                )
                session.add(identity)
                try:
                    session.commit()
                except IntegrityError:
                    # A concurrent first request may have provisioned the same subject.
                    session.rollback()
                    identity = session.scalar(self._identity_query(user))
                    if identity is None:
                        raise
            else:
                identity.user.username = user.username
                identity.user.email = user.email
                session.commit()

            return replace(
                user,
                internal_user_id=identity.user.id,
                username=identity.user.username,
                email=identity.user.email,
            )

    @staticmethod
    def _identity_query(user: AuthenticatedUser):
        return (
            select(UserIdentity)
            .options(joinedload(UserIdentity.user))
            .where(
                UserIdentity.provider == user.provider,
                UserIdentity.subject == user.subject,
            )
        )
