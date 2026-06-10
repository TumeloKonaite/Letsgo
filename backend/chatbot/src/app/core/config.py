from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from .content_paths import default_content_data_dir, default_conversation_storage_dir

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PERSISTENT_STORAGE_ROOT = Path("/persistent-storage")


def _default_content_data_dir() -> Path:
    return default_content_data_dir(
        project_root=PROJECT_ROOT,
        persistent_storage_root=PERSISTENT_STORAGE_ROOT,
    )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(PROJECT_ROOT / ".env"),),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    openai_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_API_KEY"),
    )
    openai_model: str = Field(
        default="gpt-4o-mini",
        validation_alias=AliasChoices("OPENAI_MODEL"),
    )
    openai_timeout_seconds: float = Field(
        default=30.0,
        gt=0,
        validation_alias=AliasChoices("OPENAI_TIMEOUT_SECONDS"),
    )
    openai_max_retries: int = Field(
        default=2,
        ge=0,
        validation_alias=AliasChoices("OPENAI_MAX_RETRIES"),
    )
    content_data_dir: Path = Field(
        default_factory=_default_content_data_dir,
        validation_alias=AliasChoices("CONTENT_DATA_DIR"),
    )
    conversation_storage_dir: Path | None = Field(
        default=None,
        validation_alias=AliasChoices("CONVERSATION_STORAGE_DIR", "MEMORY_DIR"),
    )
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"],
        validation_alias=AliasChoices("CORS_ORIGINS"),
    )

    @field_validator("content_data_dir", "conversation_storage_dir", mode="before")
    @classmethod
    def resolve_project_path(cls, value: str | Path | None) -> Path | None:
        if value is None:
            return None
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = (PROJECT_ROOT / path).resolve()
        return path

    @field_validator("openai_api_key", mode="before")
    @classmethod
    def normalize_openai_api_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def apply_default_conversation_storage_dir(self) -> Settings:
        if self.conversation_storage_dir is None:
            self.conversation_storage_dir = default_conversation_storage_dir(
                self.content_data_dir
            )
        return self

    @field_validator("content_data_dir")
    @classmethod
    def validate_content_data_dir(cls, value: Path) -> Path:
        if not value.exists():
            raise ValueError(f"CONTENT_DATA_DIR does not exist: {value}")
        if not value.is_dir():
            raise ValueError(f"CONTENT_DATA_DIR must be a directory: {value}")
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return value

        normalized = value.strip()
        if not normalized:
            return []

        if normalized.startswith("["):
            parsed = json.loads(normalized)
            if not isinstance(parsed, list) or not all(
                isinstance(item, str) for item in parsed
            ):
                raise ValueError("CORS_ORIGINS JSON value must be a list of strings")
            return parsed

        return [origin.strip() for origin in normalized.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
