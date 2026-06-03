from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_application


def test_packages_endpoint_allows_vite_origin(tmp_path: Path) -> None:
    application = create_application(
        settings=Settings(
            database_url=f"sqlite:///{tmp_path / 'test-cors.db'}",
            keycloak_issuer="https://keycloak.example.com/realms/letsgosa",
            keycloak_audience="letsgosa-admin",
            keycloak_jwks_url="https://keycloak.example.com/realms/letsgosa/protocol/openid-connect/certs",
            keycloak_admin_role="admin",
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
