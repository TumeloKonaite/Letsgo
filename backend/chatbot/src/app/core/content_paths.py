from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA_DIR_NAME = "data"
CONVERSATIONS_DIR_NAME = "conversations"
TWIN_PROFILE_FILENAME = "twin_profile.json"
SUMMARY_FILENAME = "summary.txt"
STYLE_FILENAME = "style.txt"
LINKEDIN_FILENAME = "linkedin.pdf"
FALLBACK_PERSONALITY_FILENAME = "fallback_personality.txt"


def default_content_data_dir(
    project_root: Path | None = None,
    persistent_storage_root: Path | None = None,
) -> Path:
    root = project_root or PROJECT_ROOT
    if persistent_storage_root is not None:
        persistent_data_dir = persistent_storage_root / DEFAULT_DATA_DIR_NAME
        if persistent_data_dir.exists():
            return persistent_data_dir
    return root / DEFAULT_DATA_DIR_NAME


def default_conversation_storage_dir(content_data_dir: Path) -> Path:
    return Path(content_data_dir) / CONVERSATIONS_DIR_NAME


def resolve_data_dir(
    data_dir: Path | None = None,
    project_root: Path | None = None,
    persistent_storage_root: Path | None = None,
) -> Path:
    if data_dir is not None:
        return Path(data_dir)
    return default_content_data_dir(
        project_root=project_root,
        persistent_storage_root=persistent_storage_root,
    )


def resolve_data_path(
    filename: str,
    data_dir: Path | None = None,
    project_root: Path | None = None,
    persistent_storage_root: Path | None = None,
) -> Path:
    return (
        resolve_data_dir(
            data_dir=data_dir,
            project_root=project_root,
            persistent_storage_root=persistent_storage_root,
        )
        / filename
    )
