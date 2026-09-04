from pathlib import Path

from app.main import create_application
from fastapi.testclient import TestClient

from tests.api.firebase_auth_helpers import build_test_settings


def test_packages_endpoint_allows_vite_origin(tmp_path: Path) -> None:
    application = create_application(
        settings=build_test_settings(
            f"sqlite:///{tmp_path / 'test-cors.db'}",
            cors_allow_origins=("http://localhost:5173",),
        )
    )

    with TestClient(application) as client:
        response = client.options(
            "/api/packages",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_packages_endpoint_allows_firebase_hosting_origin(tmp_path: Path) -> None:
    application = create_application(
        settings=build_test_settings(
            f"sqlite:///{tmp_path / 'test-firebase-cors.db'}",
            cors_allow_origins=("https://letsgodb.web.app",),
        )
    )

    with TestClient(application) as client:
        response = client.options(
            "/api/packages",
            headers={
                "Origin": "https://letsgodb.web.app",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://letsgodb.web.app"
