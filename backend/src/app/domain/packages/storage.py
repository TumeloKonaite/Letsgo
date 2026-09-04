from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Protocol
from uuid import uuid4

SUPPORTED_IMAGE_CONTENT_TYPES = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/webp",
    }
)

_CONTENT_TYPE_TO_EXTENSION = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}

DEFAULT_PACKAGE_IMAGE_FIELD_NAME = "file"


class StorageError(Exception):
    """Raised when object storage operations fail."""


class StorageAuthenticationError(StorageError):
    """Raised when the storage backend rejects credentials."""


class StorageBucketNotFoundError(StorageError):
    """Raised when the configured bucket does not exist."""


class InvalidImageFormatError(ValueError):
    """Raised when an uploaded file is not a supported image."""


class ImageTooLargeError(ValueError):
    """Raised when an uploaded file exceeds the maximum allowed size."""


@dataclass(frozen=True, slots=True)
class StoredObject:
    object_name: str
    url: str
    content_type: str
    size: int


class StorageService(Protocol):
    def upload_image(
        self, object_name: str, content: bytes, content_type: str
    ) -> StoredObject:
        """Upload an image and return its stored metadata."""

    def delete_image(self, object_name: str) -> None:
        """Delete an image from object storage."""

    def get_public_url(self, object_name: str) -> str:
        """Build the public URL for a stored object."""

    def extract_object_name(self, url: str) -> str | None:
        """Recover the object name from a public URL when needed."""


def validate_image_upload(content: bytes, max_size_bytes: int) -> str:
    if len(content) > max_size_bytes:
        raise ImageTooLargeError(
            f"Image exceeds maximum upload size of {max_size_bytes} bytes."
        )

    detected_content_type = detect_image_content_type(content)
    if detected_content_type is None:
        raise InvalidImageFormatError(
            "Unsupported image format. Supported formats: JPEG, PNG, WebP."
        )

    return detected_content_type


def detect_image_content_type(content: bytes) -> str | None:
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    return None


def build_package_image_object_name(
    package_slug: str, original_filename: str, content_type: str
) -> str:
    extension = _CONTENT_TYPE_TO_EXTENSION[content_type]
    filename_stem = _sanitize_filename_stem(original_filename)
    package_segment = _sanitize_path_segment(package_slug)
    unique_suffix = uuid4().hex
    return str(
        PurePosixPath("packages")
        / package_segment
        / f"{filename_stem}-{unique_suffix}.{extension}"
    )


def _sanitize_filename_stem(filename: str) -> str:
    raw_stem = PurePosixPath(filename).stem or "image"
    sanitized = re.sub(r"[^a-z0-9]+", "-", raw_stem.strip().lower()).strip("-")
    return sanitized or "image"


def _sanitize_path_segment(value: str) -> str:
    sanitized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return sanitized or "package"
