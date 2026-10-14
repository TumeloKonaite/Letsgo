from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from app.auth.clerk_auth import (
    ClerkAuthService,
    ClerkTokenExpiredError,
    ClerkTokenValidationError,
)
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


@pytest.fixture(scope="module")
def signing_keys() -> tuple[bytes, str]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem.decode()


def token(private_key: bytes, **overrides) -> str:
    now = datetime.now(UTC)
    claims = {
        "sub": "user_test",
        "iss": "https://clerk.example.invalid",
        "azp": "https://letsgosa.vercel.app",
        "iat": now,
        "exp": now + timedelta(minutes=5),
        "email": "admin@example.invalid",
        "admin": True,
    }
    claims.update(overrides)
    return jwt.encode(claims, private_key, algorithm="RS256")


def service(public_key: str) -> ClerkAuthService:
    return ClerkAuthService(
        secret_key="sk_test_synthetic",
        jwt_key=public_key,
        issuer_url="https://clerk.example.invalid",
        authorized_parties=("https://letsgosa.vercel.app",),
        admin_claim="admin",
    )


def test_valid_clerk_token_is_mapped_to_authenticated_user(signing_keys) -> None:
    private_key, public_key = signing_keys

    user = service(public_key).verify_token(token(private_key))

    assert user.subject == "user_test"
    assert user.email == "admin@example.invalid"
    assert user.roles == frozenset({"admin"})
    assert user.provider == "clerk"
    assert user.internal_user_id is None
    assert not hasattr(user, "claims")


def test_verified_identity_is_resolved_through_provider_neutral_repository(
    signing_keys,
) -> None:
    private_key, public_key = signing_keys

    class IdentityRepository:
        def __init__(self) -> None:
            self.seen = None

        def resolve_or_provision(self, user):
            self.seen = user
            return replace(user, internal_user_id="internal-user-1")

    repository = IdentityRepository()
    adapter = ClerkAuthService(
        secret_key="sk_test_synthetic",
        jwt_key=public_key,
        issuer_url="https://clerk.example.invalid",
        authorized_parties=("https://letsgosa.vercel.app",),
        admin_claim="admin",
        identity_repository=repository,
    )

    user = adapter.verify_token(token(private_key))

    assert repository.seen is not None
    assert repository.seen.subject == "user_test"
    assert user.internal_user_id == "internal-user-1"


def test_token_from_unauthorized_party_is_rejected(signing_keys) -> None:
    private_key, public_key = signing_keys

    with pytest.raises(ClerkTokenValidationError):
        service(public_key).verify_token(
            token(private_key, azp="https://attacker.example.invalid")
        )


def test_expired_token_is_rejected_distinctly(signing_keys) -> None:
    private_key, public_key = signing_keys

    with pytest.raises(ClerkTokenExpiredError):
        service(public_key).verify_token(
            token(private_key, exp=datetime.now(UTC) - timedelta(seconds=1))
        )


@pytest.mark.parametrize("value", [False, "true", 1, None, ["admin"]])
def test_admin_role_requires_boolean_true(signing_keys, value) -> None:
    private_key, public_key = signing_keys
    user = service(public_key).verify_token(token(private_key, admin=value))
    assert user.roles == frozenset()


@pytest.mark.parametrize(
    "overrides",
    [
        {"iss": "https://untrusted.example.invalid"},
        {"aud": "another-api"},
        {"sub": ""},
        {"sub": 123},
        {"azp": None},
        {"exp": None},
    ],
)
def test_invalid_claims_are_rejected(signing_keys, overrides) -> None:
    private_key, public_key = signing_keys
    with pytest.raises(ClerkTokenValidationError):
        service(public_key).verify_token(token(private_key, **overrides))


def test_invalid_signature_is_rejected(signing_keys) -> None:
    _, public_key = signing_keys
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with pytest.raises(ClerkTokenValidationError):
        service(public_key).verify_token(token(other_key))


def test_malformed_token_is_rejected(signing_keys) -> None:
    _, public_key = signing_keys
    with pytest.raises(ClerkTokenValidationError):
        service(public_key).verify_token("not.a.jwt")


def test_claim_fallbacks_and_custom_role_mapping(signing_keys) -> None:
    private_key, public_key = signing_keys
    adapter = ClerkAuthService(
        secret_key="sk_test_synthetic",
        jwt_key=public_key,
        issuer_url="https://clerk.example.invalid",
        authorized_parties=("https://letsgosa.vercel.app",),
        admin_claim="app_admin",
    )
    user = adapter.verify_token(
        token(
            private_key,
            username=42,
            name="Test User",
            email=None,
            email_address="test@example.invalid",
            app_admin=True,
            roles=["superuser"],
            internal_user_id="untrusted",
        )
    )
    assert user.username == "Test User"
    assert user.email == "test@example.invalid"
    assert user.roles == frozenset({"admin"})
    assert user.internal_user_id is None
