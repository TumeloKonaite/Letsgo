from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.domain.auth.models import AuthenticatedUser

if TYPE_CHECKING:
    from firebase_admin import App
else:
    App = Any


class FirebaseTokenValidationError(Exception):
    """Raised when a Firebase ID token cannot be validated."""


class FirebaseTokenExpiredError(FirebaseTokenValidationError):
    """Raised when a Firebase ID token is expired."""


class FirebaseAuthService:
    def __init__(self, firebase_app: App) -> None:
        self._firebase_app = firebase_app

    def verify_token(self, token: str) -> AuthenticatedUser:
        from firebase_admin import auth as firebase_auth

        try:
            claims = firebase_auth.verify_id_token(token, app=self._firebase_app)
        except firebase_auth.ExpiredIdTokenError as exc:
            raise FirebaseTokenExpiredError("Token expired") from exc
        except (
            firebase_auth.CertificateFetchError,
            firebase_auth.InvalidIdTokenError,
            firebase_auth.RevokedIdTokenError,
            firebase_auth.UserDisabledError,
            ValueError,
        ) as exc:
            raise FirebaseTokenValidationError("Invalid token") from exc

        subject = claims.get("uid") or claims.get("sub")
        if not isinstance(subject, str) or not subject.strip():
            raise FirebaseTokenValidationError("Token subject is missing")

        email = claims.get("email")
        name = claims.get("name")
        return AuthenticatedUser(
            subject=subject,
            username=name if isinstance(name, str) else email if isinstance(email, str) else None,
            email=email if isinstance(email, str) else None,
            claims=dict(claims),
        )
