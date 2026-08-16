"""A collection of utility constants and functions for media processing.

This module centralizes MIME type mappings, supported extensions, and other
media-related constants to make them easily accessible and extendable across
the project.
"""

from typing import Final

#: Centralized mapping of MIME types to file extensions.
MIME_TO_EXTENSION_MAP: Final[dict[str, str]] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/svg+xml": ".svg",
    "image/webp": ".webp",
    "image/x-icon": ".ico",
    "image/vnd.microsoft.icon": ".ico",
    "audio/mpeg": ".mp3",
    "audio/mp4": ".m4a",
    "audio/ogg": ".ogg",
    "audio/wav": ".wav",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/ogg": ".ogv",
}

#: Derived set of audio extensions for validation.
AUDIO_EXTENSIONS: Final[frozenset[str]] = frozenset(
    ext for mime, ext in MIME_TO_EXTENSION_MAP.items() if mime.startswith("audio/")
)

#: Derived set of video extensions for validation.
VIDEO_EXTENSIONS: Final[frozenset[str]] = frozenset(
    ext for mime, ext in MIME_TO_EXTENSION_MAP.items() if mime.startswith("video/")
)

#: Common aliases for image extensions not covered by the primary MIME map.
IMAGE_EXTENSION_ALIASES: Final[frozenset[str]] = frozenset({".jpeg"})

#: Mapping from alias extensions to their canonical counterparts.
IMAGE_EXTENSION_ALIAS_MAP: Final[dict[str, str]] = {
    ".jpeg": ".jpg",
}

#: Derived set of image extensions for validation.
IMAGE_EXTENSIONS: Final[frozenset[str]] = frozenset(
    ext for mime, ext in MIME_TO_EXTENSION_MAP.items() if mime.startswith("image/")
).union(IMAGE_EXTENSION_ALIASES)


def normalize_extension(ext: str | None) -> str | None:
    """Normalize a file extension to its canonical form.

    This helper ensures consistent handling of alias extensions (e.g. ``.jpeg``)
    by converting them to the canonical extension used by
    :func:`get_extension_for_mime` (e.g. ``.jpg``).

    The input extension is treated case-insensitively, and a leading dot is
    added if missing. Unknown extensions are returned in their normalized form.
    """
    if not ext:
        return None

    # Normalize by lowercasing, stripping whitespace, and ensuring a leading dot.
    normalized = ext.lower().strip()
    if not normalized.startswith("."):
        normalized = f".{normalized}"

    return IMAGE_EXTENSION_ALIAS_MAP.get(normalized, normalized)


def get_extension_for_mime(mime_type: str | None) -> str | None:
    """Returns the canonical file extension for a given MIME type.

    This helper provides a centralized way to access the MIME_TO_EXTENSION_MAP,
    handling case-insensitivity and potential fallback logic in one place.

    Args:
        mime_type: The MIME type string to look up (e.g., "image/jpeg").

    Returns:
        The corresponding file extension (e.g., ".jpg") if found, otherwise None.
    """
    if not mime_type:
        return None
    main_mime_type = mime_type.strip().split(";", 1)[0].strip()
    return MIME_TO_EXTENSION_MAP.get(main_mime_type.lower())


#: Standard prefix for data URIs.
DATA_URI_PREFIX: Final[str] = "data:"
