from __future__ import annotations

from app.main import create_application
from fastapi.testclient import TestClient

from tests.api.clerk_auth_helpers import build_test_settings


def test_application_startup_does_not_require_external_credentials(
    tmp_path, monkeypatch
) -> None:
    database_url = f"sqlite:///{tmp_path / 'startup.db'}"
    application = create_application(settings=build_test_settings(database_url))

    def _fail_client_creation(*args, **kwargs):
        raise AssertionError("storage client should not be created during startup")

    monkeypatch.setattr(
        "app.infrastructure.storage.gcs_storage.Client",
        _fail_client_creation,
    )
    with TestClient(application) as client:
        response = client.get("/health")

    assert response.status_code == 200
