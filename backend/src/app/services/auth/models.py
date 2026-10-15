"""Define application identity; a subject is scoped to its provider, not a database ID."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    subject: str
    provider: str
    internal_user_id: str | None = None
    username: str | None = None
    email: str | None = None
    roles: frozenset[str] = field(default_factory=frozenset)
