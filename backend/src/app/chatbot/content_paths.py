"""Centralize chatbot resource filenames relative to the configured data directory."""

from __future__ import annotations

from pathlib import Path

DEFAULT_DATA_DIR_NAME = "data"
CONVERSATIONS_DIR_NAME = "conversations"
TWIN_PROFILE_FILENAME = "twin_profile.json"
SUMMARY_FILENAME = "summary.txt"
STYLE_FILENAME = "style.txt"
LINKEDIN_FILENAME = "linkedin.pdf"
FALLBACK_PERSONALITY_FILENAME = "fallback_personality.txt"


def resolve_data_path(filename: str, data_dir: Path) -> Path:
    return Path(data_dir) / filename
