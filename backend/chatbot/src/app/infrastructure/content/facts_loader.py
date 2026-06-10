from __future__ import annotations

import json
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from src.app.core.content_paths import TWIN_PROFILE_FILENAME, resolve_data_path


class ContentLoadError(RuntimeError):
    """Raised when runtime content cannot be loaded."""


class MissingContentError(ContentLoadError, FileNotFoundError):
    """Raised when a required content file is missing."""


class InvalidContentError(ContentLoadError):
    """Raised when a content file exists but cannot be parsed or read."""


class FactsLoader:
    def __init__(
        self,
        data_dir: Path,
        filename: str = TWIN_PROFILE_FILENAME,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.filename = filename

    @property
    def path(self) -> Path:
        return resolve_data_path(self.filename, data_dir=self.data_dir)

    def load(self) -> dict[str, Any]:
        try:
            payload = self.path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise MissingContentError(
                f"Required profile file not found: {self.path}"
            ) from exc
        except OSError as exc:
            raise InvalidContentError(
                f"Unable to read profile file: {self.path}"
            ) from exc

        try:
            facts = json.loads(payload)
        except JSONDecodeError as exc:
            raise InvalidContentError(
                f"Invalid JSON in profile file: {self.path}"
            ) from exc

        if not isinstance(facts, dict):
            raise InvalidContentError(
                f"Expected a JSON object in profile file: {self.path}"
            )

        missing_fields = [
            field_name
            for field_name in ("name", "full_name")
            if not facts.get(field_name)
        ]
        if missing_fields:
            missing_fields_display = ", ".join(missing_fields)
            raise InvalidContentError(
                f"Missing required profile fields in {self.path}: {missing_fields_display}"
            )

        return facts
