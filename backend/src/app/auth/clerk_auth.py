"""Verify Clerk credentials and translate trusted claims into application identity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from clerk_backend_api import AuthenticateRequestOptions, authenticate_request
from clerk_backend_api.security.types import TokenVerificationErrorReason

from app.domain.auth.models import AuthenticatedUser
from app.domain.auth.provider import AuthenticationError
from app.domain.auth.repository import IdentityRepository


class ClerkTokenValidationError(AuthenticationError):
    """Raised when a Clerk session token cannot be validated."""


class ClerkTokenExpiredError(ClerkTokenValidationError):
    """Raised when a Clerk session token is expired."""


@dataclass(frozen=True, slots=True)
class _BearerRequest:
    """Minimal request shape accepted by Clerk's backend authentication helper."""

    headers: dict[str, str]


class ClerkAuthService:
    """Verify Clerk session tokens using explicitly configured trust settings."""

    def __init__(
        self,
        *,
        secret_key: str,
        jwt_key: str,
        issuer_url: str,
        authorized_parties: tuple[str, ...],
        admin_claim: str,
        identity_repository: IdentityRepository | None = None,
    ) -> None:
        """Store the JWT key, issuer, and browser origins trusted by the API."""
        self._admin_claim = admin_claim
        self._issuer_url = issuer_url.rstrip("/")
        self._identity_repository = identity_repository
        self._verification_options = AuthenticateRequestOptions(
            secret_key=secret_key,
            jwt_key=jwt_key,
            authorized_parties=list(authorized_parties),
            clock_skew_in_ms=0,
            accepts_token=["session_token"],
        )

    def verify_token(self, token: str) -> AuthenticatedUser:
        """Verify a Clerk JWT and convert its claims to the domain user model."""
        try:
            state = authenticate_request(
                _BearerRequest(headers={"Authorization": f"Bearer {token}"}),
                self._verification_options,
            )
        except (TypeError, ValueError, OverflowError) as exc:
            # The SDK can surface malformed numeric-date claims as built-ins.
            raise ClerkTokenValidationError("Invalid credentials") from exc
        if not state.is_signed_in:
            if state.reason is TokenVerificationErrorReason.TOKEN_EXPIRED:
                raise ClerkTokenExpiredError("Invalid credentials")
            raise ClerkTokenValidationError("Invalid credentials")

        claims = state.payload
        if not isinstance(claims, dict) or not _has_required_claims(claims):
            raise ClerkTokenValidationError("Invalid credentials")
        if claims["iss"] != self._issuer_url:
            raise ClerkTokenValidationError("Invalid credentials")

        subject = claims["sub"]

        # Only the configured boolean claim grants admin; raw claims stay here.
        user = AuthenticatedUser(
            subject=subject,
            username=_first_string(claims, "username", "name"),
            email=_first_string(claims, "email", "email_address"),
            provider="clerk",
            roles=frozenset({"admin"})
            if claims.get(self._admin_claim) is True
            else frozenset(),
        )
        if self._identity_repository is None:
            return user
        return self._identity_repository.resolve_or_provision(user)


def _first_string(claims: dict[str, Any], *names: str) -> str | None:
    """Return the first populated string from a list of possible claim names."""
    for name in names:
        value = claims.get(name)
        if isinstance(value, str) and value:
            return value
    return None


def _has_required_claims(claims: dict[str, Any]) -> bool:
    """Require the stable identity and trust claims of a Clerk session JWT."""
    return (
        isinstance(claims.get("sub"), str)
        and bool(claims["sub"])
        and isinstance(claims.get("iss"), str)
        and bool(claims["iss"])
        and isinstance(claims.get("azp"), str)
        and bool(claims["azp"])
        and _is_timestamp(claims.get("iat"))
        and _is_timestamp(claims.get("exp"))
    )


def _is_timestamp(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)
