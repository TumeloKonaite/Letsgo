from typing import Annotated

import pytest
from app.api.routes.admin.auth import router
from app.core.dependencies import get_authentication_provider, require_admin
from app.domain.auth.models import AuthenticatedUser
from app.domain.auth.provider import AuthenticationError
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient


class AlternateProvider:
    def __init__(self):
        self.calls = []

    def verify_token(self, token):
        self.calls.append(token)
        if token == "invalid":
            raise AuthenticationError("sensitive provider validation details")
        return AuthenticatedUser(
            subject="same-subject",
            provider="alternate",
            roles=frozenset({"admin"}) if token == "admin" else frozenset(),
        )


@pytest.fixture
def boundary():
    app = FastAPI()
    provider = AlternateProvider()
    app.dependency_overrides[get_authentication_provider] = lambda: provider
    app.include_router(router)

    @app.get("/protected")
    def protected(user: Annotated[AuthenticatedUser, Depends(require_admin)]):
        return {"subject": user.subject}

    with TestClient(app) as client:
        yield client, provider


@pytest.mark.parametrize(
    "header", [None, "", "Basic abc", "Bearer", "Bearer ", "Bearer a b", "Bearer a\tb"]
)
def test_extraction_rejects_missing_or_malformed_credentials(boundary, header):
    client, provider = boundary
    response = client.get(
        "/protected", headers={} if header is None else {"Authorization": header}
    )
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {"detail": "Invalid or missing credentials"}
    assert provider.calls == []


def test_provider_failure_is_sanitized(boundary):
    client, _ = boundary
    response = client.get("/protected", headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {"detail": "Invalid or missing credentials"}


def test_alternate_provider_and_separate_authorization(boundary):
    client, _ = boundary
    headers = {"Authorization": "bEaReR user"}
    identity = client.get("/admin/auth/me", headers=headers)
    assert identity.status_code == 200
    assert identity.json()["provider"] == "alternate"
    assert identity.json()["sub"] == "same-subject"
    assert "claims" not in identity.json()
    denied = client.get("/protected", headers=headers)
    assert denied.status_code == 403
    assert "www-authenticate" not in denied.headers
    assert (
        client.get("/protected", headers={"Authorization": "Bearer admin"}).status_code
        == 200
    )


def test_provider_subject_is_not_an_internal_or_cross_provider_id():
    first = AuthenticatedUser(subject="same", provider="firebase")
    second = AuthenticatedUser(subject="same", provider="clerk")
    assert first != second
    assert first.internal_user_id is second.internal_user_id is None
    assert first.subject == second.subject == "same"
