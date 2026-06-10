from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


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


class FileConversationStore(ConversationStore):
    def __init__(self, storage_dir: Path) -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _file_path_for(self, session_id: str) -> Path:
        return self.storage_dir / f"{session_id}.json"

    def load(self, session_id: str) -> list[dict[str, str]]:
        file_path = self._file_path_for(session_id)
        try:
            with file_path.open("r", encoding="utf-8") as file:
                conversation = json.load(file)
        except FileNotFoundError:
            return []
        except json.JSONDecodeError:
            logger.warning(
                "Conversation file is corrupted. Falling back to empty history.",
                extra={"session_id": session_id, "file_path": str(file_path)},
            )
            return []

        if not isinstance(conversation, list):
            logger.warning(
                "Conversation file has an invalid format. Falling back to empty history.",
                extra={"session_id": session_id, "file_path": str(file_path)},
            )
            return []

        return conversation

    def save(self, session_id: str, messages: list[dict[str, str]]) -> None:
        file_path = self._file_path_for(session_id)
        with file_path.open("w", encoding="utf-8") as file:
            json.dump(messages, file, indent=2, ensure_ascii=False)

    def list_sessions(self) -> list[dict[str, Any]]:
        sessions: list[dict[str, Any]] = []
        for file_path in self.storage_dir.glob("*.json"):
            conversation = self.load(file_path.stem)
            last_message = conversation[-1].get("content") if conversation else None
            sessions.append(
                {
                    "session_id": file_path.stem,
                    "message_count": len(conversation),
                    "last_message": last_message,
                }
            )
        return sessions
