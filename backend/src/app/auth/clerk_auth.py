"""Verify Clerk credentials and translate trusted claims into application identity."""

from __future__ import annotations

from typing import Any

import jwt

from app.domain.auth.models import AuthenticatedUser
from app.domain.auth.provider import AuthenticationError


class ClerkTokenValidationError(AuthenticationError):
    """Raised when a Clerk session token cannot be validated."""


class ClerkTokenExpiredError(ClerkTokenValidationError):
    """Raised when a Clerk session token is expired."""


class ClerkAuthService:
    """Verify Clerk session tokens using explicitly configured trust settings."""

    def __init__(
        self,
        *,
        jwt_key: str,
        issuer_url: str,
        authorized_parties: tuple[str, ...],
        admin_claim: str,
    ) -> None:
        """Store the JWT key, issuer, and browser origins trusted by the API."""
        self._admin_claim = admin_claim
        self._jwt_key = jwt_key
        self._issuer_url = issuer_url.rstrip("/")
        self._authorized_parties = frozenset(authorized_parties)

    def verify_token(self, token: str) -> AuthenticatedUser:
        """Verify a Clerk JWT and convert its claims to the domain user model."""
        try:
            claims: dict[str, Any] = jwt.decode(
                token,
                self._jwt_key,
                algorithms=["RS256"],
                issuer=self._issuer_url,
                options={"require": ["exp", "iat", "sub"]},
            )
        except jwt.ExpiredSignatureError as exc:
            raise ClerkTokenExpiredError("Token expired") from exc
        except jwt.PyJWTError as exc:
            raise ClerkTokenValidationError("Invalid token") from exc

        # A valid signature alone does not establish an allowed browser origin.
        authorized_party = claims.get("azp")
        if (
            not isinstance(authorized_party, str)
            or authorized_party not in self._authorized_parties
        ):
            raise ClerkTokenValidationError("Invalid token")

        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject:
            raise ClerkTokenValidationError("Invalid token")

        # Only the configured boolean claim grants admin; raw claims stay here.
        return AuthenticatedUser(
            subject=subject,
            username=_first_string(claims, "username", "name"),
            email=_first_string(claims, "email", "email_address"),
            provider="clerk",
            roles=frozenset({"admin"})
            if claims.get(self._admin_claim) is True
            else frozenset(),
        )


def _first_string(claims: dict[str, Any], *names: str) -> str | None:
    """Return the first populated string from a list of possible claim names."""
    for name in names:
        value = claims.get(name)
        if isinstance(value, str) and value:
            return value
    return None
