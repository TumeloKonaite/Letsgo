from __future__ import annotations

from base64 import urlsafe_b64decode
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
import hmac
import json
from typing import Any, Protocol
from urllib.error import URLError
from urllib.request import urlopen

from app.domain.auth.models import AuthenticatedUser

RS256_DIGEST_INFO_PREFIX = bytes.fromhex("3031300d060960864801650304020105000420")


class TokenValidationError(Exception):
    """Raised when a JWT cannot be validated."""


class MissingKeycloakKeyError(TokenValidationError):
    """Raised when no matching JWKS key exists for a token."""


class TokenExpiredError(TokenValidationError):
    """Raised when a JWT is no longer valid."""


class JWKSFetcher(Protocol):
    def __call__(self, url: str) -> dict[str, Any]:
        """Return a JWKS document."""


def fetch_jwks(url: str, timeout_seconds: float = 5.0) -> dict[str, Any]:
    try:
        with urlopen(url, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, json.JSONDecodeError) as exc:
        raise TokenValidationError("Unable to load Keycloak signing keys.") from exc


@dataclass(slots=True)
class ParsedToken:
    header: dict[str, Any]
    payload: dict[str, Any]
    signature: bytes
    signing_input: bytes


class KeycloakJWTValidator:
    def __init__(
        self,
        *,
        issuer: str,
        audience: str,
        jwks_url: str,
        timeout_seconds: float = 5.0,
        jwks_fetcher: JWKSFetcher | None = None,
    ) -> None:
        self._issuer = issuer.rstrip("/")
        self._audience = audience
        self._jwks_url = jwks_url
        self._timeout_seconds = timeout_seconds
        self._jwks_fetcher = jwks_fetcher or (
            lambda url: fetch_jwks(url, timeout_seconds=self._timeout_seconds)
        )
        self._jwks_cache: dict[str, Any] | None = None

    @property
    def issuer(self) -> str:
        return self._issuer

    @property
    def jwks_url(self) -> str:
        return self._jwks_url

    def validate_token(self, token: str) -> AuthenticatedUser:
        parsed_token = self._parse_token(token)
        self._verify_signature(parsed_token)
        self._validate_claims(parsed_token.payload)
        return self._to_user(parsed_token.payload)

    def _parse_token(self, token: str) -> ParsedToken:
        parts = token.split(".")
        if len(parts) != 3:
            raise TokenValidationError("Token must contain three segments.")

        header_segment, payload_segment, signature_segment = parts
        signing_input = f"{header_segment}.{payload_segment}".encode("ascii")

        try:
            header = json.loads(self._base64url_decode(header_segment))
            payload = json.loads(self._base64url_decode(payload_segment))
            signature = self._base64url_decode_bytes(signature_segment)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise TokenValidationError("Token is malformed.") from exc

        if not isinstance(header, dict) or not isinstance(payload, dict):
            raise TokenValidationError("Token is malformed.")

        return ParsedToken(
            header=header,
            payload=payload,
            signature=signature,
            signing_input=signing_input,
        )

    def _verify_signature(self, token: ParsedToken) -> None:
        if token.header.get("alg") != "RS256":
            raise TokenValidationError("Unsupported JWT signing algorithm.")

        keys = self._get_candidate_keys(token.header.get("kid"))
        for key in keys:
            if self._verify_rs256_signature(token.signing_input, token.signature, key):
                return

        raise TokenValidationError("Token signature is invalid.")

    def _get_candidate_keys(self, kid: str | None) -> list[dict[str, Any]]:
        jwks = self._load_jwks(refresh=False)
        keys = self._select_keys(jwks, kid)
        if keys:
            return keys

        refreshed_jwks = self._load_jwks(refresh=True)
        refreshed_keys = self._select_keys(refreshed_jwks, kid)
        if refreshed_keys:
            return refreshed_keys

        raise MissingKeycloakKeyError("No matching Keycloak signing key found.")

    def _load_jwks(self, *, refresh: bool) -> dict[str, Any]:
        if refresh or self._jwks_cache is None:
            jwks = self._jwks_fetcher(self.jwks_url)
            keys = jwks.get("keys")
            if not isinstance(keys, list):
                raise TokenValidationError("Keycloak JWKS payload is invalid.")
            self._jwks_cache = jwks
        return self._jwks_cache

    def _select_keys(self, jwks: dict[str, Any], kid: str | None) -> list[dict[str, Any]]:
        keys = [
            key
            for key in jwks["keys"]
            if isinstance(key, dict) and key.get("kty") == "RSA" and key.get("use") in {None, "sig"}
        ]
        if kid is None:
            return keys
        return [key for key in keys if key.get("kid") == kid]

    def _validate_claims(self, claims: dict[str, Any]) -> None:
        issuer = claims.get("iss")
        if issuer != self.issuer:
            raise TokenValidationError("Token issuer is invalid.")

        audience = claims.get("aud")
        valid_audience = (
            audience == self._audience
            if isinstance(audience, str)
            else self._audience in audience
            if isinstance(audience, list)
            else False
        )
        if not valid_audience:
            raise TokenValidationError("Token audience is invalid.")

        exp = claims.get("exp")
        if not isinstance(exp, int | float):
            raise TokenValidationError("Token expiration is invalid.")

        now = datetime.now(tz=UTC).timestamp()
        if exp <= now:
            raise TokenExpiredError("Token has expired.")

    def _to_user(self, claims: dict[str, Any]) -> AuthenticatedUser:
        roles = set()

        direct_roles = claims.get("roles")
        if isinstance(direct_roles, list):
            roles.update(role for role in direct_roles if isinstance(role, str))

        realm_access = claims.get("realm_access")
        if isinstance(realm_access, dict):
            realm_roles = realm_access.get("roles")
            if isinstance(realm_roles, list):
                roles.update(role for role in realm_roles if isinstance(role, str))

        resource_access = claims.get("resource_access")
        if isinstance(resource_access, dict):
            for access in resource_access.values():
                if not isinstance(access, dict):
                    continue
                client_roles = access.get("roles")
                if isinstance(client_roles, list):
                    roles.update(role for role in client_roles if isinstance(role, str))

        return AuthenticatedUser(
            subject=str(claims.get("sub", "")),
            username=self._read_optional_str(claims.get("preferred_username")),
            email=self._read_optional_str(claims.get("email")),
            roles=frozenset(roles),
            claims=claims,
        )

    def _verify_rs256_signature(
        self,
        signing_input: bytes,
        signature: bytes,
        key: dict[str, Any],
    ) -> bool:
        try:
            modulus = int.from_bytes(self._base64url_decode_bytes(key["n"]), "big")
            exponent = int.from_bytes(self._base64url_decode_bytes(key["e"]), "big")
        except (KeyError, ValueError) as exc:
            raise TokenValidationError("Keycloak JWKS key is invalid.") from exc

        if modulus <= 0 or exponent <= 0:
            raise TokenValidationError("Keycloak JWKS key is invalid.")

        key_length = (modulus.bit_length() + 7) // 8
        signature_int = int.from_bytes(signature, "big")
        encoded_message = pow(signature_int, exponent, modulus).to_bytes(key_length, "big")

        digest = sha256(signing_input).digest()
        digest_info = RS256_DIGEST_INFO_PREFIX + digest
        padding_length = key_length - len(digest_info) - 3
        if padding_length < 8:
            raise TokenValidationError("Keycloak JWKS key is invalid.")

        expected = b"\x00\x01" + (b"\xff" * padding_length) + b"\x00" + digest_info
        return hmac.compare_digest(encoded_message, expected)

    def _base64url_decode(self, value: str) -> str:
        return self._base64url_decode_bytes(value).decode("utf-8")

    def _base64url_decode_bytes(self, value: str) -> bytes:
        padding = "=" * ((4 - len(value) % 4) % 4)
        return urlsafe_b64decode(f"{value}{padding}")

    def _read_optional_str(self, value: Any) -> str | None:
        return value if isinstance(value, str) and value else None
