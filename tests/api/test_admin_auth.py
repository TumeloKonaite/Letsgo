from __future__ import annotations

from base64 import urlsafe_b64encode
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
import json

from fastapi.testclient import TestClient
import pytest

from app.core.auth.keycloak import KeycloakJWTValidator
from app.core.config import Settings
from app.infrastructure.database.models import Package, PackageImage
from app.main import create_application

RS256_DIGEST_INFO_PREFIX = bytes.fromhex("3031300d060960864801650304020105000420")
TEST_KID = "test-key"
TEST_SERVER_URL = "https://keycloak.example.com"
TEST_REALM = "letsgosa"
TEST_CLIENT_ID = "letsgosa-admin"
TEST_AUDIENCE = "letsgosa-admin"
TEST_JWK = {
    "kty": "RSA",
    "use": "sig",
    "alg": "RS256",
    "kid": TEST_KID,
    "n": "xCjGp4WD3Hpj4czGtOGYQb2qN7g0LrzXha1XMWtUnNpefnkEgIOEBtTNxn9IATDpA65_JK8KqPUm2aO0XfnaCHY4grJbm3TtJijcx_obVd-kUBxhid2oTCw_00nckN7MC1bII_PbB5c5UryPQyTQqOFUVidNZL7Z-FOqKgP9GE4QG645AC1toyRjSQbfyY3FPxPBD1AqcUAgWF25KWMeOaY8p9LZ_TK2yhqYk94Ta5rkkCyDYiJ6DIn1EMIq9hBdLK7GLvuLwwVUyDzn_TnqZYrJC5Bc5owOlo8d5EijPpx7IaZCIOKe8MXWYOhFelciAwkk_gf4BcenvYi2WPuZvQ",
    "e": "AQAB",
}
TEST_PRIVATE_EXPONENT = "qoIjQ-Tb3N-KSPFeXEaouaRq_KoiuemukeU-IJgCYaGzd84r6qXnMqTyBbQH2_ku4uNgY3vAEWOflJknJHUVYDubHYh59qRpq7zjRPUTo86Vnok9A8DoFOZ1yGywzEDOLqENsaq73lpGGrQK97tdoR7U11qsfIElKSVYidMTwnY4SaxP0NAtdLlAKF_4wIIv89MRWCRZmxF9Tklpwqp7R8BTr9ayJ80cT0rrJoKzbgwzLeOzLSBQomdgFtwcP76UAPxrjI1J6qWl_tDVRBJNTCw7NFFg5ItTbKPNQeIA1l-6gl1U1eAf0S7w5bXFdb9l5_Bn_lV8NmfrYdO74MkbhQ"


@dataclass(frozen=True, slots=True)
class SeededAdminClient:
    client: TestClient
    package_id: int
    image_id: int


def _base64url_encode(data: bytes) -> str:
    return urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _base64url_decode_int(value: str) -> int:
    padding = "=" * ((4 - len(value) % 4) % 4)
    return int.from_bytes(__import__("base64").urlsafe_b64decode(f"{value}{padding}"), "big")


def _sign_rs256(signing_input: bytes) -> bytes:
    modulus = _base64url_decode_int(TEST_JWK["n"])
    private_exponent = _base64url_decode_int(TEST_PRIVATE_EXPONENT)
    key_length = (modulus.bit_length() + 7) // 8

    digest = sha256(signing_input).digest()
    digest_info = RS256_DIGEST_INFO_PREFIX + digest
    padding_length = key_length - len(digest_info) - 3
    encoded_message = b"\x00\x01" + (b"\xff" * padding_length) + b"\x00" + digest_info
    signature_int = pow(int.from_bytes(encoded_message, "big"), private_exponent, modulus)
    return signature_int.to_bytes(key_length, "big")


def _build_token(
    *,
    roles: list[str],
    expires_at: datetime | None = None,
    audience: str = TEST_AUDIENCE,
) -> str:
    now = datetime.now(tz=UTC)
    payload = {
        "iss": f"{TEST_SERVER_URL}/realms/{TEST_REALM}",
        "sub": "admin-user-1",
        "aud": audience,
        "exp": int((expires_at or (now + timedelta(minutes=5))).timestamp()),
        "iat": int(now.timestamp()),
        "preferred_username": "admin.user",
        "email": "admin@example.com",
        "realm_access": {"roles": roles},
    }
    header = {"alg": "RS256", "typ": "JWT", "kid": TEST_KID}
    header_segment = _base64url_encode(
        json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    payload_segment = _base64url_encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
    signature_segment = _base64url_encode(_sign_rs256(signing_input))
    return f"{header_segment}.{payload_segment}.{signature_segment}"


def _build_auth_service() -> KeycloakJWTValidator:
    return KeycloakJWTValidator(
        server_url=TEST_SERVER_URL,
        realm=TEST_REALM,
        client_id=TEST_CLIENT_ID,
        audience=TEST_AUDIENCE,
        jwks_fetcher=lambda _: {"keys": [TEST_JWK]},
    )


def _seed_existing_package(session_factory) -> tuple[int, int]:
    with session_factory() as session:
        package = Package(
            title="Test Package",
            slug="test-package",
            short_description="Existing package.",
            description="Existing package for admin tests.",
            destination="Cape Town",
            duration_days=3,
            duration_nights=2,
            price_from=Decimal("1999.00"),
            currency="ZAR",
        )
        package.images.append(
            PackageImage(
                image_url="https://example.com/existing.jpg",
                alt_text="Existing image",
                sort_order=0,
                is_cover=True,
            )
        )
        session.add(package)
        session.commit()
        session.refresh(package)
        return package.id, package.images[0].id


@pytest.fixture
def admin_client(tmp_path) -> SeededAdminClient:
    database_url = f"sqlite:///{tmp_path / 'admin.db'}"
    application = create_application(
        settings=Settings(
            database_url=database_url,
            keycloak_server_url=TEST_SERVER_URL,
            keycloak_realm=TEST_REALM,
            keycloak_client_id=TEST_CLIENT_ID,
            keycloak_audience=TEST_AUDIENCE,
        )
    )

    with TestClient(application) as client:
        application.state.keycloak_auth_service = _build_auth_service()
        package_id, image_id = _seed_existing_package(application.state.db_session_factory)
        yield SeededAdminClient(client=client, package_id=package_id, image_id=image_id)


def test_valid_keycloak_token_is_accepted(admin_client: SeededAdminClient) -> None:
    response = admin_client.client.get(
        "/api/admin/auth/me",
        headers={"Authorization": f"Bearer {_build_token(roles=['admin'])}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "sub": "admin-user-1",
        "username": "admin.user",
        "email": "admin@example.com",
        "roles": ["admin"],
    }


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("POST", "/api/admin/packages", {
            "title": "New Package",
            "slug": "new-package",
            "short_description": "Short description",
            "description": "Long description",
            "destination": "Johannesburg",
            "duration_days": 5,
            "duration_nights": 4,
            "price_from": "5999.00",
            "currency": "ZAR",
            "is_active": True,
            "status": "draft",
            "is_published": False,
            "is_featured": False,
            "display_order": 1,
        }),
        ("PUT", "/api/admin/packages/{package_id}", {
            "title": "Updated Package",
            "slug": "updated-package",
            "short_description": "Short description",
            "description": "Long description",
            "destination": "Pretoria",
            "duration_days": 4,
            "duration_nights": 3,
            "price_from": "7999.00",
            "currency": "ZAR",
            "is_active": True,
            "status": "published",
            "is_published": True,
            "is_featured": True,
            "display_order": 2,
        }),
        ("PATCH", "/api/admin/packages/{package_id}", {
            "title": "Patched Package",
        }),
        ("DELETE", "/api/admin/packages/{package_id}", None),
        ("POST", "/api/admin/packages/{package_id}/images", {
            "image_url": "https://example.com/new-image.jpg",
            "alt_text": "New image",
            "sort_order": 1,
            "is_cover": False,
        }),
        ("DELETE", "/api/admin/packages/{package_id}/images?image_id={image_id}", None),
    ],
)
def test_missing_token_returns_401_for_all_admin_package_mutations(
    admin_client: SeededAdminClient,
    method: str,
    path: str,
    payload: dict[str, object] | None,
) -> None:
    response = admin_client.client.request(
        method,
        path.format(package_id=admin_client.package_id, image_id=admin_client.image_id),
        json=payload,
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Missing bearer token"}


def test_invalid_token_returns_401(admin_client: SeededAdminClient) -> None:
    valid_token = _build_token(roles=["admin"])
    invalid_token = f"{valid_token[:-1]}{'A' if valid_token[-1] != 'A' else 'B'}"

    response = admin_client.client.post(
        "/api/admin/packages",
        headers={"Authorization": f"Bearer {invalid_token}"},
        json={
            "title": "New Package",
            "slug": "new-package",
            "short_description": "Short description",
            "description": "Long description",
            "destination": "Johannesburg",
            "duration_days": 5,
            "duration_nights": 4,
            "price_from": "5999.00",
            "currency": "ZAR",
            "is_active": True,
            "status": "draft",
            "is_published": False,
            "is_featured": False,
            "display_order": 1,
        },
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token"}


def test_expired_token_returns_401(admin_client: SeededAdminClient) -> None:
    expired_token = _build_token(roles=["admin"], expires_at=datetime.now(tz=UTC) - timedelta(minutes=1))

    response = admin_client.client.post(
        "/api/admin/packages",
        headers={"Authorization": f"Bearer {expired_token}"},
        json={
            "title": "New Package",
            "slug": "new-package",
            "short_description": "Short description",
            "description": "Long description",
            "destination": "Johannesburg",
            "duration_days": 5,
            "duration_nights": 4,
            "price_from": "5999.00",
            "currency": "ZAR",
            "is_active": True,
            "status": "draft",
            "is_published": False,
            "is_featured": False,
            "display_order": 1,
        },
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Token expired"}


def test_user_with_admin_role_can_access_protected_routes(admin_client: SeededAdminClient) -> None:
    response = admin_client.client.post(
        "/api/admin/packages",
        headers={"Authorization": f"Bearer {_build_token(roles=['admin'])}"},
        json={
            "title": "New Package",
            "slug": "new-package",
            "short_description": "Short description",
            "description": "Long description",
            "destination": "Johannesburg",
            "duration_days": 5,
            "duration_nights": 4,
            "price_from": "5999.00",
            "currency": "ZAR",
            "is_active": True,
            "status": "draft",
            "is_published": False,
            "is_featured": False,
            "display_order": 1,
        },
    )

    assert response.status_code == 201
    assert response.json()["slug"] == "new-package"


def test_user_without_admin_role_receives_403(admin_client: SeededAdminClient) -> None:
    response = admin_client.client.patch(
        f"/api/admin/packages/{admin_client.package_id}",
        headers={"Authorization": f"Bearer {_build_token(roles=['editor'])}"},
        json={"title": "Forbidden Update"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Admin role required"}


def test_application_fails_fast_when_keycloak_configuration_is_missing(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'missing-keycloak.db'}"

    with pytest.raises(
        ValueError,
        match="Missing required Keycloak configuration: KEYCLOAK_SERVER_URL, KEYCLOAK_REALM, KEYCLOAK_CLIENT_ID, KEYCLOAK_AUDIENCE",
    ):
        create_application(settings=Settings(database_url=database_url))
