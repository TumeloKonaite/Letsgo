"""Define provider-neutral external identity persistence."""

from typing import Protocol

from app.domain.auth.models import AuthenticatedUser


class IdentityRepository(Protocol):
    def resolve_or_provision(self, user: AuthenticatedUser) -> AuthenticatedUser:
        """Resolve provider+subject or provision a new internal application user."""
        ...
