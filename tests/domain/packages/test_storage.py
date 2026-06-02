from __future__ import annotations

import pytest

from app.domain.packages.storage import (
    ImageTooLargeError,
    InvalidImageFormatError,
    build_package_image_object_name,
    validate_image_upload,
)


def test_build_package_image_object_name_generates_unique_names() -> None:
    first_object_name = build_package_image_object_name(
        "Cape Town Tour",
        "Table Mountain View.JPG",
        "image/jpeg",
    )
    second_object_name = build_package_image_object_name(
        "Cape Town Tour",
        "Table Mountain View.JPG",
        "image/jpeg",
    )

    assert first_object_name.startswith("packages/cape-town-tour/table-mountain-view-")
    assert first_object_name.endswith(".jpg")
    assert second_object_name.startswith("packages/cape-town-tour/table-mountain-view-")
    assert first_object_name != second_object_name


@pytest.mark.parametrize(
    ("content", "expected_content_type"),
    [
        (b"\xff\xd8\xff\xe0" + b"jpeg", "image/jpeg"),
        (b"\x89PNG\r\n\x1a\n" + b"png", "image/png"),
        (b"RIFF\x00\x00\x00\x00WEBP" + b"webp", "image/webp"),
    ],
)
def test_validate_image_upload_accepts_supported_formats(
    content: bytes,
    expected_content_type: str,
) -> None:
    assert validate_image_upload(content, max_size_bytes=1024) == expected_content_type


def test_validate_image_upload_rejects_unsupported_formats() -> None:
    with pytest.raises(InvalidImageFormatError):
        validate_image_upload(b"not-an-image", max_size_bytes=1024)


def test_validate_image_upload_rejects_oversized_files() -> None:
    with pytest.raises(ImageTooLargeError):
        validate_image_upload(b"\x89PNG\r\n\x1a\n" + (b"x" * 32), max_size_bytes=8)
