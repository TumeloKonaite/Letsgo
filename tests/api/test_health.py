from app.main import app


def test_health_endpoint_returns_ok(client) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "application": "LetsGoSA API",
        "environment": "development",
    }


def test_application_startup_sets_dependencies() -> None:
    from fastapi.testclient import TestClient

    with TestClient(app):
        assert app.state.started is True
        assert app.state.package_service is not None
        assert app.state.settings.app_name == "LetsGoSA API"
