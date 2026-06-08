from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ContactSubmission:
    first_name: str
    last_name: str
    email: str
    phone: str
    subject: str
    message: str
