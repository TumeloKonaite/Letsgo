"""Specify token verification and normalized failures independently of any provider SDK."""

from typing import Protocol

from app.domain.auth.models import AuthenticatedUser


class AuthenticationError(Exception):
    """Credentials could not be authenticated; details must not reach clients."""


class AuthenticationProvider(Protocol):
    def verify_token(self, token: str) -> AuthenticatedUser:
        """Validate provider trust and normalize identity, or raise AuthenticationError.

        Implementations must validate signature, issuer, expiry and configured
        audience/authorized-party constraints. Never log tokens or raw claims.
        """
        ...
