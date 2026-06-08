from __future__ import annotations

from email.message import EmailMessage
from unittest.mock import MagicMock, patch

import pytest

from app.domain.contact import ContactSubmission
from app.infrastructure.email import EmailDeliveryError
from app.infrastructure.email.smtp_email_sender import SMTPEmailSender


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


def test_smtp_email_sender_sends_contact_request(
    contact_submission: ContactSubmission,
) -> None:
    sender = SMTPEmailSender(
        host="smtp.example.com",
        port=587,
        username="mailer",
        password="secret",
        from_email="hello@letsgosouth.africa",
        to_email="sales@letsgosouth.africa",
        use_tls=True,
    )

    with patch("app.infrastructure.email.smtp_email_sender.smtplib.SMTP") as smtp:
        client = MagicMock()
        smtp.return_value.__enter__.return_value = client

        sender.send_contact_request(contact_submission)

    client.ehlo.assert_called()
    client.starttls.assert_called_once_with()
    client.login.assert_called_once_with("mailer", "secret")
    client.send_message.assert_called_once()

    sent_message = client.send_message.call_args.args[0]
    assert isinstance(sent_message, EmailMessage)
    assert (
        sent_message["Subject"] == "LetsGoSouth contact enquiry: Custom safari planning"
    )
    assert sent_message["From"] == "hello@letsgosouth.africa"
    assert sent_message["To"] == "sales@letsgosouth.africa"
    assert sent_message["Reply-To"] == "jane@example.com"
    assert "First name: Jane" in sent_message.get_content()
    assert (
        "I would like help planning a private guided trip in September."
        in sent_message.get_content()
    )


def test_smtp_email_sender_raises_when_configuration_is_invalid(
    contact_submission: ContactSubmission,
) -> None:
    sender = SMTPEmailSender(
        host=None,
        port=587,
        username=None,
        password=None,
        from_email="hello@letsgosouth.africa",
        to_email="sales@letsgosouth.africa",
        use_tls=True,
    )

    with pytest.raises(EmailDeliveryError, match="Unable to send contact request."):
        sender.send_contact_request(contact_submission)
