from __future__ import annotations

from unittest.mock import Mock

from fastapi.testclient import TestClient
import pytest

from app.domain.contact import ContactServiceError, ContactSubmission
from app.main import create_application
from tests.api.firebase_auth_helpers import build_test_settings


@pytest.fixture
def contact_payload() -> dict[str, str]:
    return {
        "first_name": "Jane",
        "last_name": "Doe",
        "email": "Jane.Doe@example.com",
        "phone": "+27 82 123 4567",
        "subject": "Custom safari planning",
        "message": "I would like help planning a private guided trip in September.",
    }


@pytest.fixture
def contact_submission(contact_payload: dict[str, str]) -> ContactSubmission:
    return ContactSubmission(
        first_name="Jane",
        last_name="Doe",
        email="jane.doe@example.com",
        phone="+27 82 123 4567",
        subject="Custom safari planning",
        message="I would like help planning a private guided trip in September.",
    )


@pytest.fixture
def contact_client(tmp_path) -> TestClient:
    settings = build_test_settings(
        f"sqlite:///{tmp_path / 'contact.db'}",
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_username="mailer",
        smtp_password="secret",
        smtp_from_email="hello@letsgosouth.africa",
        contact_to_email="sales@letsgosouth.africa",
        smtp_use_tls=True,
    )
    application = create_application(settings=settings)

    with TestClient(application) as client:
        yield client


@pytest.fixture
def contact_service_override(contact_client: TestClient):
    service = Mock()
    contact_client.app.state.contact_service = service
    return service


def test_contact_route_returns_success(
    contact_client: TestClient,
    contact_payload: dict[str, str],
    contact_submission: ContactSubmission,
    contact_service_override,
) -> None:
    response = contact_client.post("/api/contact", json=contact_payload)

    assert response.status_code == 200
    assert response.json() == {"message": "Contact request submitted successfully."}
    contact_service_override.submit_contact_request.assert_called_once_with(
        contact_submission
    )


def test_contact_route_returns_error_response_on_service_failure(
    contact_client: TestClient,
    contact_payload: dict[str, str],
    contact_service_override,
) -> None:
    contact_service_override.submit_contact_request.side_effect = ContactServiceError(
        "smtp failure"
    )

    response = contact_client.post("/api/contact", json=contact_payload)

    assert response.status_code == 500
    assert response.json() == {"detail": "Unable to send contact request."}


def test_contact_route_rejects_invalid_payload(
    contact_client: TestClient,
    contact_service_override,
) -> None:
    response = contact_client.post(
        "/api/contact",
        json={
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "not-an-email",
            "phone": "+27 82 123 4567",
            "subject": "Hi",
            "message": "short",
        },
    )

    assert response.status_code == 422
    contact_service_override.submit_contact_request.assert_not_called()


def test_contact_route_requires_all_required_fields(
    contact_client: TestClient,
    contact_service_override,
) -> None:
    response = contact_client.post(
        "/api/contact",
        json={
            "first_name": "Jane",
            "last_name": "Doe",
            "phone": "+27 82 123 4567",
            "subject": "Custom safari planning",
            "message": "I would like help planning a private guided trip in September.",
        },
    )

    assert response.status_code == 422
    contact_service_override.submit_contact_request.assert_not_called()
