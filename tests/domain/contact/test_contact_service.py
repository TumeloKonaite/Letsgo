from __future__ import annotations

from unittest.mock import Mock, call

import pytest

from app.domain.contact import ContactService, ContactServiceError, ContactSubmission
from app.infrastructure.email import EmailDeliveryError


@pytest.fixture
def contact_submission() -> ContactSubmission:
    return ContactSubmission(
        first_name="Jane",
        last_name="Doe",
        email="jane@example.com",
        phone="+27 82 123 4567",
        subject="Custom safari planning",
        message="I would like help planning a private guided trip in September.",
    )


def test_contact_service_submits_contact_request(
    contact_submission: ContactSubmission,
) -> None:
    tracker = Mock()
    email_sender = Mock()
    repository = Mock()
    repository.create.return_value = 101
    tracker.attach_mock(repository, "repository")
    tracker.attach_mock(email_sender, "email_sender")
    service = ContactService(email_sender=email_sender, repository=repository)

    service.submit_contact_request(contact_submission)

    repository.create.assert_called_once_with(contact_submission)
    email_sender.send_contact_request.assert_called_once_with(contact_submission)
    repository.mark_email_sent.assert_called_once_with(101)
    repository.mark_email_failed.assert_not_called()
    assert tracker.mock_calls == [
        call.repository.create(contact_submission),
        call.email_sender.send_contact_request(contact_submission),
        call.repository.mark_email_sent(101),
    ]


def test_contact_service_marks_failed_when_email_delivery_fails(
    contact_submission: ContactSubmission,
) -> None:
    tracker = Mock()
    email_sender = Mock()
    repository = Mock()
    repository.create.return_value = 202
    email_sender.send_contact_request.side_effect = EmailDeliveryError("smtp failure")
    tracker.attach_mock(repository, "repository")
    tracker.attach_mock(email_sender, "email_sender")
    service = ContactService(email_sender=email_sender, repository=repository)

    with pytest.raises(ContactServiceError, match="Unable to send contact request."):
        service.submit_contact_request(contact_submission)

    repository.create.assert_called_once_with(contact_submission)
    repository.mark_email_failed.assert_called_once_with(202, "smtp failure")
    repository.mark_email_sent.assert_not_called()
    assert tracker.mock_calls == [
        call.repository.create(contact_submission),
        call.email_sender.send_contact_request(contact_submission),
        call.repository.mark_email_failed(202, "smtp failure"),
    ]


def test_contact_service_stops_when_repository_insert_fails(
    contact_submission: ContactSubmission,
) -> None:
    email_sender = Mock()
    repository = Mock()
    repository.create.side_effect = RuntimeError("database unavailable")
    service = ContactService(email_sender=email_sender, repository=repository)

    with pytest.raises(ContactServiceError, match="Unable to send contact request."):
        service.submit_contact_request(contact_submission)

    repository.create.assert_called_once_with(contact_submission)
    email_sender.send_contact_request.assert_not_called()
    repository.mark_email_sent.assert_not_called()
    repository.mark_email_failed.assert_not_called()
