from __future__ import annotations

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
        "azp": "https://travel.example.invalid",
        "iat": now,
        "exp": now + timedelta(minutes=5),
        "email": "admin@example.invalid",
        "admin": True,
    }
    claims.update(overrides)
    return jwt.encode(claims, private_key, algorithm="RS256")


def service(public_key: str) -> ClerkAuthService:
    return ClerkAuthService(
        jwt_key=public_key,
        issuer_url="https://clerk.example.invalid",
        authorized_parties=("https://travel.example.invalid",),
    )


def test_valid_clerk_token_is_mapped_to_authenticated_user(signing_keys) -> None:
    private_key, public_key = signing_keys

    user = service(public_key).verify_token(token(private_key))

    assert user.subject == "user_test"
    assert user.email == "admin@example.invalid"
    assert user.claims["admin"] is True


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
