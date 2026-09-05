from __future__ import annotations

from dataclasses import dataclass, field

from app.auth.clerk_auth import ClerkTokenExpiredError, ClerkTokenValidationError
from app.core.config import Settings
from app.domain.auth.models import AuthenticatedUser

TEST_CLERK_ADMIN_CLAIM = "admin"
TEST_ADMIN_TOKEN = "admin-token"
TEST_EDITOR_TOKEN = "editor-token"
TEST_EXPIRED_TOKEN = "expired-token"
TEST_JWT_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA5nhAUsF4yGsMxkuAnXMX
yzHzrpah8+DlwvHp8nifUbbfbWe5n1RXimcCEKnrcwxOqh0C2mWjpXl1eSZUIBuY
CU4ikpI1O3vb7wY2wpYGDR9Adw2BGKpo/+NKA6uUiWRhj24YN/P5PuctqrNRnRRg
q3S9BOu9zy7ce82VJ5o0tPVUsTsQ3TtzcLDvZtCfJewY5JbjEao1t3ZIGGkFJW+z
4vsc+dEdhHvh5L8dOEPxUoH+YTx0GfO1PJQOyT+B+IkvRyhlgUYVprMTwmKI2/xj
iD80dQjQOIQJW8nX7TLOZdFpUhdbzQXj/hTDAXECnCRka9NLDxPmWxPvrQC4n2k1
gQIDAQAB
-----END PUBLIC KEY-----"""


@dataclass(slots=True)
class StubClerkAuthService:
    users: dict[str, AuthenticatedUser] = field(default_factory=dict)
    expired_tokens: set[str] = field(default_factory=set)

    def add_token(self, token: str, user: AuthenticatedUser) -> None:
        self.users[token] = user

    def verify_token(self, token: str) -> AuthenticatedUser:
        if token in self.expired_tokens:
            raise ClerkTokenExpiredError("Token expired")
        if token not in self.users:
            raise ClerkTokenValidationError("Invalid token")
        return self.users[token]


def build_test_settings(database_url: str, **overrides) -> Settings:
    values = {
        "environment": "test",
        "database_url": database_url,
        "cors_allow_origins": ("http://localhost:5173",),
        "clerk_secret_key": "sk_test_synthetic",
        "clerk_jwt_key": TEST_JWT_KEY,
        "clerk_issuer_url": "https://clerk.example.invalid",
        "clerk_authorized_parties": ("http://localhost:5173",),
        "clerk_admin_claim": TEST_CLERK_ADMIN_CLAIM,
        "storage_provider": "gcs",
        "gcp_project_id": "test-project",
        "gcs_bucket_name": "test-package-images",
        "gcs_public_base_url": "https://storage.example.invalid/images",
    }
    values.update(overrides)
    if (
        "cors_allow_origins" in overrides
        and "clerk_authorized_parties" not in overrides
    ):
        values["clerk_authorized_parties"] = values["cors_allow_origins"]
    return Settings(**values)


def build_user(
    *,
    subject: str,
    email: str,
    admin: bool,
    username: str | None = None,
    claims: dict[str, object] | None = None,
) -> AuthenticatedUser:
    resolved_claims = {TEST_CLERK_ADMIN_CLAIM: admin}
    if claims:
        resolved_claims.update(claims)
    return AuthenticatedUser(
        subject=subject,
        username=username or email,
        email=email,
        provider="clerk",
        roles=frozenset({"admin"})
        if resolved_claims.get("admin") is True
        else frozenset(),
    )


def install_stub_clerk_auth(application) -> StubClerkAuthService:
    service = StubClerkAuthService()
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
    application.state.authentication_provider = service
    return service


def bearer_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
