"""A collection of specialized media handling strategies for the MediaProcessor.

This module implements the Strategy pattern for the MediaProcessor. Each handler
is responsible for a single, specific type of media processing, such as
extracting Base64 data, relocating local files, or handling external videos.
This separation of concerns makes the system more modular, testable, and
extensible.
"""

from __future__ import annotations

import base64
import binascii
import logging
import re  # type: ignore
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Final

from bs4 import BeautifulSoup
from bs4.element import Tag

from ..core.dom_utils import snapshot_iterator
from ..core.media_utils import (
    AUDIO_EXTENSIONS,
    DATA_URI_PREFIX,
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
)

if TYPE_CHECKING:
    from .processor import MediaProcessor

log = logging.getLogger(__name__)


class BaseMediaHandler(ABC):
    """Abstract base class for all media handling strategies."""

    def __init__(self, processor: MediaProcessor):
        """Initializes the handler with a reference to the parent processor.

        Args:
            processor: The parent MediaProcessor instance, providing access to
                configuration, counters, and shared utilities.
        """
        self.processor = processor
        self.context = processor.context

    @abstractmethod
    def can_handle(self, tag: Tag) -> bool:
        """Determines if this handler can process the given tag.

        Args:
            tag: The BeautifulSoup Tag to evaluate.

        Returns:
            True if the handler is responsible for this tag, False otherwise.
        """

    @abstractmethod
    def handle(self, tag: Tag, soup: BeautifulSoup, file_path: Path) -> bool:
        """Executes the media processing logic for the tag.

        Args:
            tag: The BeautifulSoup Tag to process.
            soup: The root BeautifulSoup object.
            file_path: The path of the HTML file containing the tag.

        Returns:
            True if the tag was successfully handled, False otherwise.
        """


class UnsupportedMediaHandler(BaseMediaHandler):
    """Handles defensive degradation of unsupported media tags (Layer D)."""

    # Whitelist prefixes for data-* attributes that provide human-readable context.
    _DATA_ATTR_WHITELIST_PREFIXES: Final = (
        "data-description",
        "data-label",
        "data-alt",
        "data-caption",
        "data-summary",
    )
    # Blacklist substrings for data-* attributes that suggest tracking/identifiers.
    _DATA_ATTR_BLACKLIST_SUBSTRINGS: Final = (
        "id",
        "token",
        "track",
        "analytics",
        "metric",
        "session",
        "fingerprint",
        "uid",
        "guid",
        "cid",
        "bid",
    )

    def can_handle(self, tag: Tag) -> bool:
        """Checks for <script> or <canvas> tags."""
        return tag.name in ("script", "canvas")

    def handle(self, tag: Tag, soup: BeautifulSoup, file_path: Path) -> bool:
        """Replaces the tag with a standard placeholder.

        Retains selected non-executable metadata from the original tag
        (e.g. aria-label, title, and descriptive data-* attributes) so that
        downstream consumers have context about the omitted element while
        still avoiding executable content.
        """
        # This logic is adapted from the original _handle_defensive_degradation
        placeholder = soup.new_tag("p", attrs={"class": "media-placeholder"})

        # Preserve a minimal, safe subset of attributes for context
        retained_attrs = {
            attr: tag.attrs[attr]
            for attr in ("aria-label", "title")
            if attr in tag.attrs
        }

        # Descriptive data-* attributes, but only non-empty string values and
        # excluding obvious tracking/identifier-related keys to avoid leaking
        # sensitive metadata.
        for attr_name, attr_value in tag.attrs.items():
            if not (
                isinstance(attr_name, str)
                and attr_name.startswith("data-")
                and isinstance(attr_value, (str, int, float))
                and str(attr_value).strip()
            ):
                continue

            # Whitelist descriptive attributes by prefix
            if attr_name.startswith(self._DATA_ATTR_WHITELIST_PREFIXES):
                retained_attrs[attr_name] = attr_value
                continue

            # Skip attributes whose name suggests tracking/identifiers/tokens
            lowered_name = attr_name.lower()
            if any(
                substr in lowered_name
                for substr in self._DATA_ATTR_BLACKLIST_SUBSTRINGS
            ):
                continue

        em_tag = soup.new_tag("em")
        em_tag.string = "[Multimedia Element Omitted: Script or interactive component unsupported by portable layouts]"
        placeholder.append(em_tag)
        tag.replace_with(placeholder)
        self.processor.purged_count += 1
        return True


class ExternalVideoHandler(BaseMediaHandler):
    """Handles external video embeds (Layer C)."""

    def can_handle(self, tag: Tag) -> bool:
        """Checks for video iframes, embeds, or objects from known domains."""
        if tag.name not in ("iframe", "embed", "object"):
            return False
        src_attr = tag.get("src") or tag.get("data")
        return isinstance(src_attr, str) and bool(
            self.processor.video_domain_rx.search(src_attr),
        )

    def handle(self, tag: Tag, soup: BeautifulSoup, file_path: Path) -> bool:
        """Wraps the external video in a protected semantic block."""
        # This logic is directly from the original _handle_external_video
        src_attr = tag.get("src") or tag.get("data")
        if not isinstance(src_attr, str):
            return False

        if tag.name in ("object", "embed"):
            content_type = tag.get("type")
            if isinstance(content_type, str) and not (
                content_type.lower().startswith("video/")
                or content_type.lower() == "application/x-shockwave-flash"
            ):
                return False

        wrapper_tag = soup.new_tag("div", attrs={"class": "protected video-block"})
        wrapper_tag["data-video-src"] = src_attr

        self.processor.copy_preserved_attributes(tag, wrapper_tag)

        img_tag = self.processor.create_video_placeholder_img(tag, soup)
        wrapper_tag.append(img_tag)

        for child in snapshot_iterator(tag.children):
            wrapper_tag.append(child.extract())

        tag.replace_with(wrapper_tag)
        self.processor.external_video_count += 1
        return True


class Base64MediaHandler(BaseMediaHandler):
    """Handles embedded Base64 media (Layer A)."""

    def can_handle(self, tag: Tag) -> bool:
        """Checks for img/image tags with a 'data:' URI."""
        if tag.name not in ("img", "image"):
            return False

        # Prefer a non-empty src attribute, otherwise fall back to XLINK_HREF.
        src = tag.get("src")
        if not isinstance(src, str) or not src.strip():
            src = tag.get(self.processor.XLINK_HREF_ATTR)

        return (
            isinstance(src, str)
            and src.startswith(DATA_URI_PREFIX)
            and ";base64," in src
        )

    def _parse_data_uri(self, src_attr: str) -> tuple[str, str]:
        """Parses a Data URI and returns the MIME type and encoded data.

        Args:
            src_attr: The Data URI string to parse.

        Returns:
            A tuple containing the MIME type and the Base64-encoded data.

        Raises:
            ValueError: If the Data URI format is invalid, not Base64 encoded,
                or if the MIME type is missing.
        """
        if not src_attr.startswith(DATA_URI_PREFIX) or "," not in src_attr:
            raise ValueError(f"Invalid Data URI format: {src_attr[:100]}")

        header, encoded_data = src_attr.split(",", 1)
        if ";base64" not in header:
            raise ValueError("Data URI is not base64 encoded")

        mime_match = re.search(r"data:([^;,]*)", header)
        if not mime_match or not (mime_type := mime_match[1].strip()):
            raise ValueError(
                "MIME type is missing or could not be parsed from Data URI",
            )

        return mime_type, encoded_data

    def handle(self, tag: Tag, soup: BeautifulSoup, file_path: Path) -> bool:
        """Extracts, saves, and replaces the Base64 data."""
        # Prefer a non-empty src attribute, otherwise fall back to XLINK_HREF.
        src_attr = tag.get("src")
        if not isinstance(src_attr, str) or not src_attr.strip():
            src_attr = tag.get(self.processor.XLINK_HREF_ATTR)

        if not isinstance(src_attr, str):
            return False

        try:
            mime_type, encoded_data = self._parse_data_uri(src_attr)
            binary_data = base64.b64decode(encoded_data, validate=True)
            ext = self.processor.get_extension_from_mime(mime_type)
            if not ext:
                raise ValueError(f"Unknown or unsupported MIME type: {mime_type}")

            # Get media type and increment counter (e.g., local_image_count)
            media_type = self.processor.get_media_type_and_increment_counter(ext)

        except (ValueError, binascii.Error) as e:  # NOSONAR
            log.warning("Failed to process Base64 data for tag %s: %s", tag.name, e)
            self.processor.error_count += 1
            return False

        hash_val = self.processor.get_sha256_hash(binary_data)
        asset_filename = f"asset_{hash_val}{ext}"

        # Per spec, Base64 assets go into the 'extracted' directory
        relative_path = self.processor.save_asset_to_sibling_dir(
            "extracted",
            asset_filename,
            binary_data,
        )
        tag["src"] = relative_path
        if tag.has_attr(self.processor.XLINK_HREF_ATTR):
            del tag[self.processor.XLINK_HREF_ATTR]

        self.processor.base64_count += 1

        # If it's an image, wrap it in a figure for semantic consistency
        if media_type == "images":
            figure_tag = soup.new_tag("figure", attrs={"class": "image-block"})
            self.processor.copy_preserved_attributes(tag, figure_tag)
            # The id should remain on the media element, not move to the figure,
            # to avoid breaking CSS or JS selectors. This also prevents duplicate
            # IDs in the DOM, as copy_preserved_attributes copies the id.
            if "id" in figure_tag.attrs:
                del figure_tag["id"]
            tag.wrap(figure_tag)

        return True


_SIBLING_MEDIA_SUBDIRS: Final = frozenset({"images", "audio", "video", "extracted"})


class LocalMediaHandler(BaseMediaHandler):
    """Handles local media assets (Layer B)."""

    def can_handle(self, tag: Tag) -> bool:
        """Checks for tags with local media file paths."""
        if tag.name not in ("img", "image", "audio", "video", "object"):
            return False

        # Check main src, poster, data, xlink:href, and any child <source> tags
        src_attrs = [
            tag.get("src"),
            tag.get("data"),
            tag.get("poster"),
            tag.get(self.processor.XLINK_HREF_ATTR),
        ]
        src_attrs.extend([source.get("src") for source in tag.find_all("source")])

        return any(
            (
                isinstance(src_attr, str)
                and not src_attr.startswith(
                    ("http://", "https://", "//", DATA_URI_PREFIX),  # NOSONAR
                )
                and Path(src_attr).suffix.lower()
                in (AUDIO_EXTENSIONS | VIDEO_EXTENSIONS | IMAGE_EXTENSIONS)
            )
            for src_attr in src_attrs
        )

    def _is_already_normalized(self, src_value: str) -> bool:
        """
        Return True if the given src/poster/xlink:href value already points
        into one of the sibling media directories managed by the processor.

        This is used to avoid re-processing normalized paths during
        multi-pass runs over the same DOM or HTML.
        """
        # Guard against non-string or empty values
        if not isinstance(src_value, str) or not src_value:
            return False

        return next(
            (
                True
                for dirname in _SIBLING_MEDIA_SUBDIRS
                if src_value.startswith(f"{dirname}/") or f"/{dirname}/" in src_value
            ),
            "asset_" in src_value,
        )

    def handle(self, tag: Tag, soup: BeautifulSoup, file_path: Path) -> bool:
        """Relocates local assets and normalizes the tag, including sources and posters."""
        processed_something = False

        # Create a list of (tag, attribute_name) tuples to process
        assets_to_process = []
        if tag.has_attr("src"):
            assets_to_process.append((tag, "src"))
        if tag.has_attr("data"):
            assets_to_process.append((tag, "data"))
        if tag.has_attr("poster"):
            assets_to_process.append((tag, "poster"))
        if tag.has_attr(self.processor.XLINK_HREF_ATTR):
            assets_to_process.append((tag, self.processor.XLINK_HREF_ATTR))

        assets_to_process.extend(
            (source_tag, "src")
            for source_tag in tag.find_all("source")
            if source_tag.has_attr("src")
        )
        for asset_tag, attr_name in assets_to_process:
            src_attr = asset_tag[attr_name]
            asset_info = self.processor.read_local_asset(src_attr, file_path)

            if not asset_info:
                continue

            binary_data, ext = asset_info
            hash_val = self.processor.get_sha256_hash(binary_data)
            asset_filename = f"asset_{hash_val}{ext}"
            media_type = self.processor.get_media_type_and_increment_counter(ext)
            relative_path = self.processor.save_asset_to_sibling_dir(
                media_type,
                asset_filename,
                binary_data,
            )

            asset_tag[attr_name] = relative_path
            processed_something = True

        if not processed_something:
            return False

        # Wrap the main tag in a <figure>
        media_class_map = {
            "img": "image-block",
            "image": "image-block",
            "audio": "audio-block",
            "video": "video-block",
        }
        media_class = media_class_map.get(tag.name, "unknown-block")
        if tag.name in ("audio", "video"):
            tag["controls"] = ""

        figure_tag = soup.new_tag("figure", attrs={"class": media_class})
        self.processor.copy_preserved_attributes(tag, figure_tag)
        # The id should remain on the media element, not move to the figure,
        # to avoid breaking CSS or JS selectors. This also prevents duplicate
        # IDs in the DOM, as copy_preserved_attributes copies the id.
        if "id" in figure_tag.attrs:
            del figure_tag["id"]

        tag.wrap(figure_tag)
        return True


def get_media_handlers(processor: MediaProcessor) -> list[BaseMediaHandler]:
    """Returns an ordered list of media handlers for processing.

    The order defines the priority of execution. For example, unsupported media
    is handled first to prevent other handlers from attempting to process it.

    Args:
        processor: The parent MediaProcessor instance.

    Returns:
        A list of initialized media handler instances.
    """
    return [
        UnsupportedMediaHandler(processor),
        ExternalVideoHandler(processor),
        Base64MediaHandler(processor),
        LocalMediaHandler(processor),
    ]
