from __future__ import annotations

from dataclasses import dataclass, field

from app.auth.firebase_auth import FirebaseTokenExpiredError, FirebaseTokenValidationError
from app.core.config import Settings
from app.domain.auth.models import AuthenticatedUser

TEST_FIREBASE_PROJECT_ID = "letsgodb"
TEST_FIREBASE_ADMIN_CLAIM = "admin"
TEST_ADMIN_TOKEN = "admin-token"
TEST_EDITOR_TOKEN = "editor-token"
TEST_EXPIRED_TOKEN = "expired-token"


@dataclass(slots=True)
class StubFirebaseAuthService:
    users: dict[str, AuthenticatedUser] = field(default_factory=dict)
    expired_tokens: set[str] = field(default_factory=set)

    def add_token(self, token: str, user: AuthenticatedUser) -> None:
        self.users[token] = user

    def verify_token(self, token: str) -> AuthenticatedUser:
        if token in self.expired_tokens:
            raise FirebaseTokenExpiredError("Token expired")
        if token not in self.users:
            raise FirebaseTokenValidationError("Invalid token")
        return self.users[token]


def build_test_settings(database_url: str, **overrides) -> Settings:
    values = {
        "database_url": database_url,
        "gcp_project_id": TEST_FIREBASE_PROJECT_ID,
        "google_cloud_project": TEST_FIREBASE_PROJECT_ID,
        "firebase_project_id": TEST_FIREBASE_PROJECT_ID,
        "firebase_admin_role": TEST_FIREBASE_ADMIN_CLAIM,
        "gcs_bucket_name": "letsgosa-package-images",
        "gcs_public_base_url": "https://storage.googleapis.com/letsgosa-package-images",
    }
    values.update(overrides)
    return Settings(
        **values,
    )


def build_user(
    *,
    subject: str,
    email: str,
    admin: bool,
    username: str | None = None,
    claims: dict[str, object] | None = None,
) -> AuthenticatedUser:
    resolved_claims = {TEST_FIREBASE_ADMIN_CLAIM: admin}
    if claims:
        resolved_claims.update(claims)
    return AuthenticatedUser(
        subject=subject,
        username=username or email,
        email=email,
        claims=resolved_claims,
    )


def install_stub_firebase_auth(application) -> StubFirebaseAuthService:
    service = StubFirebaseAuthService()
    service.add_token(
        TEST_ADMIN_TOKEN,
        build_user(
            subject="admin-user-1",
            username="admin.user",
            email="admin@example.com",
            admin=True,
        ),
    )
    service.add_token(
        TEST_EDITOR_TOKEN,
        build_user(
            subject="editor-user-1",
            username="editor.user",
            email="editor@example.com",
            admin=False,
        ),
    )
    service.expired_tokens.add(TEST_EXPIRED_TOKEN)
    application.state.firebase_auth_service = service
    return service


def bearer_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
