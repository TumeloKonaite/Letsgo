from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.domain.contact.models import ContactSubmission
from app.infrastructure.email.base import EmailDeliveryError


class SMTPEmailSender:
    def __init__(
        self,
        host: str | None,
        port: int,
        username: str | None,
        password: str | None,
        from_email: str | None,
        to_email: str | None,
        use_tls: bool,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._from_email = from_email
        self._to_email = to_email
        self._use_tls = use_tls
        self._timeout_seconds = timeout_seconds

    def send_contact_request(self, submission: ContactSubmission) -> None:
        self._validate_configuration()
        message = self._build_message(submission)

        try:
            with smtplib.SMTP(
                self._host,
                self._port,
                timeout=self._timeout_seconds,
            ) as client:
                client.ehlo()
                if self._use_tls:
                    client.starttls()
                    client.ehlo()
                if self._username and self._password:
                    client.login(self._username, self._password)
                client.send_message(message)
        except (OSError, smtplib.SMTPException) as exc:
            raise EmailDeliveryError("Unable to send contact request.") from exc

    def _build_message(self, submission: ContactSubmission) -> EmailMessage:
        message = EmailMessage()
        message["Subject"] = f"LetsGoSouth contact enquiry: {submission.subject}"
        message["From"] = self._from_email
        message["To"] = self._to_email
        message["Reply-To"] = submission.email
        message.set_content(
            "\n".join(
                [
                    "New contact enquiry received.",
                    "",
                    f"First name: {submission.first_name}",
                    f"Last name: {submission.last_name}",
                    f"Email: {submission.email}",
                    f"Phone: {submission.phone}",
                    f"Subject: {submission.subject}",
                    "",
                    "Message:",
                    submission.message,
                ]
            )
        )
        return message

    def _validate_configuration(self) -> None:
        if not self._host or not self._from_email or not self._to_email:
            raise EmailDeliveryError("Unable to send contact request.")
        if self._port <= 0:
            raise EmailDeliveryError("Unable to send contact request.")
        if self._timeout_seconds <= 0:
            raise EmailDeliveryError("Unable to send contact request.")
        if bool(self._username) != bool(self._password):
            raise EmailDeliveryError("Unable to send contact request.")
