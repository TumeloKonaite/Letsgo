from app.domain.auth.models import AuthenticatedUser
from app.infrastructure.auth import PostgresIdentityRepository
from app.infrastructure.database.models import ApplicationUser, UserIdentity
from app.infrastructure.database.session import (
    create_database_engine,
    create_session_factory,
    initialize_database,
)
from sqlalchemy import select


def test_identity_is_provisioned_then_resolved_by_provider_and_subject(tmp_path) -> None:
    engine = create_database_engine(f"sqlite:///{tmp_path / 'identities.db'}")
    initialize_database(engine)
    session_factory = create_session_factory(engine)
    repository = PostgresIdentityRepository(session_factory=session_factory)

    first = repository.resolve_or_provision(
        AuthenticatedUser(
            subject="user_clerk_1",
            provider="clerk",
            username="First name",
            email="first@example.com",
            roles=frozenset({"admin"}),
        )
    )
    second = repository.resolve_or_provision(
        AuthenticatedUser(
            subject="user_clerk_1",
            provider="clerk",
            username="Updated name",
            email="updated@example.com",
        )
    )

    assert first.internal_user_id is not None
    assert second.internal_user_id == first.internal_user_id
    assert second.username == "Updated name"
    assert second.email == "updated@example.com"
    assert second.roles == frozenset()
    with session_factory() as session:
        assert len(session.scalars(select(ApplicationUser)).all()) == 1
        assert len(session.scalars(select(UserIdentity)).all()) == 1
    engine.dispose()


def test_equal_email_does_not_implicitly_link_different_subjects(tmp_path) -> None:
    engine = create_database_engine(f"sqlite:///{tmp_path / 'no-email-link.db'}")
    initialize_database(engine)
    repository = PostgresIdentityRepository(
        session_factory=create_session_factory(engine)
    )

    first = repository.resolve_or_provision(
        AuthenticatedUser(
            subject="first", provider="clerk", email="shared@example.com"
        )
    )
    second = repository.resolve_or_provision(
        AuthenticatedUser(
            subject="second", provider="clerk", email="shared@example.com"
        )
    )

    assert first.internal_user_id != second.internal_user_id
    engine.dispose()
