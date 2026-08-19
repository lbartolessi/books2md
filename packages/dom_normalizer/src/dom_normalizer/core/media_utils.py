"""A collection of utility constants and functions for media processing.

This module centralizes MIME type mappings, supported extensions, and other
media-related constants to make them easily accessible and extendable across
the project.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import EngineConfiguration


def normalize_extension(ext: str | None, config: EngineConfiguration) -> str | None:
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

    return config.image_extension_alias_map.get(normalized, normalized)


def get_extension_for_mime(mime_type: str | None, config: EngineConfiguration) -> str | None:
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
    return config.mime_to_extension_map.get(main_mime_type.lower())
