from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ConversationStore(ABC):
    @abstractmethod
    def load(self, session_id: str) -> list[dict[str, str]]:
        """Load a conversation history for a session."""

    @abstractmethod
    def save(self, session_id: str, messages: list[dict[str, str]]) -> None:
        """Persist a conversation history for a session."""

    @abstractmethod
    def list_sessions(self) -> list[dict[str, Any]]:
        """List persisted sessions with summary information."""
