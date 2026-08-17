"""A structural sanitization and multimedia asset extraction engine.

This module operates as a Stage 2 processor. Its main objective is to purge
embedded binary noise (e.g., Base64 encoded images), organize local media
resources into a strictly portable file structure, and prepare semantic
multimedia pointers for downstream processing by Pandoc and other tools. This
ensures optimized Markdown output for RAG and cross-compilation systems.

This processor must run before any text flattening or paragraph joining passes.

Analytical Blueprint:
---------------------

Based on the specification, the following logic will be mapped to the class
methods:

Global Free Functions (Module Level):
    - None present in the skeleton.

Class Methods (MediaProcessor):
    - __init__: Initializes telemetry counters and file path configurations. It
      constructs the path to the "sibling asset directory" (`[output]/[book_name]/`)
      and defines regex/lists for media detection (`VIDEO_DOMAIN_RX`,
      `AUDIO_EXTENSIONS`, `VIDEO_EXTENSIONS`).
    - _get_sha256_hash: Implements SHA-256 hashing for binary data to generate
      unique, content-addressable filenames for deduplication.
    - _get_extension_from_mime: Maps a MIME type string (e.g., 'image/png') to a
      file extension (e.g., '.png').
    - process: Orchestrates the entire pipeline. It finds all media-related tags,
      applies the `is_inside_code_block` guard, and delegates to the appropriate
      handler from the `handlers` module.
"""

from __future__ import annotations

import hashlib
import logging
import posixpath
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Final

from bs4 import BeautifulSoup
from bs4.element import Tag

from ..core import BookStyleContext, PipelineStatus
from ..core.component_registry import register_processor_factory
from ..core.dom_utils import (
    coerce_class_list,
    find_all_snapshot,
    generate_processor_metadata,
    snapshot_iterator,
)
from ..core.media_utils import (
    AUDIO_EXTENSIONS,
    IMAGE_EXTENSIONS,
    MIME_TO_EXTENSION_MAP,
    VIDEO_EXTENSIONS,
    normalize_extension,
)
from .handlers import BaseMediaHandler, get_media_handlers

log = logging.getLogger(__name__)


@register_processor_factory("media")
@register_processor_factory("media_processor")
def create_media_processor(
    context: BookStyleContext,
    **kwargs: Any,
) -> MediaProcessor:
    """Factory function to create a MediaProcessor instance."""
    book_base_name = kwargs.get(
        "book_base_name",
        getattr(context, "book_base_name", "book"),
    )
    output_directory = kwargs.get("output_directory", ".")
    book_root_path = kwargs.get("book_root_path", ".")
    return MediaProcessor(
        context=context,
        book_base_name=book_base_name,
        output_directory=output_directory,
        book_root_path=book_root_path,
    )


class MediaProcessor:
    """A structural sanitization and multimedia asset extraction engine."""

    XLINK_HREF_ATTR: Final = "xlink:href"

    def __init__(
        self,
        context: BookStyleContext,
        book_base_name: str,
        output_directory: str,
        book_root_path: str,
    ) -> None:
        """Initializes the media processor with paths and configuration.

        Args:
            context (BookStyleContext): The shared context for the book.
            book_base_name (str): The base name of the book, used to create the
                sibling asset directory (e.g., 'quantum_mechanics').
            output_directory (str): The root directory where the output and the
                sibling asset directory will be created.
            book_root_path (str): The absolute path to the book's source root,
                needed to resolve relative media paths.

        Returns:
            None

        Raises:
            FileNotFoundError: If `book_root_path` does not exist.
            NotADirectoryError: If `book_root_path` is not a directory.

        Mutations:
          - Initializes all telemetry counters to 0.
            - Constructs `self.sibling_asset_dir` path.
            - Resolves and validates `self.book_root_path`.
            - Compiles `self.video_domain_rx` from the configuration.
            - Sets `self.context`, `self.book_base_name`.
            - Raises `FileNotFoundError` or `NotADirectoryError` if `book_root_path` is invalid.

        Rules & Limits:
            - Sibling Directory Rule: The asset directory path is constructed as
              `[output_directory]/[book_base_name]`.
            - Idempotent Creation: The implementation that uses this path must create
              the directory using a method that does not fail if the directory
              already exists (e.g., `os.makedirs(..., exist_ok=True)`).
            - Instance Lifecycle: Assumes this instance is scoped to a single book.
        """

        self.context = context
        self.book_base_name = book_base_name
        self.sibling_asset_dir = Path(output_directory) / book_base_name
        try:
            self.book_root_path = Path(book_root_path).resolve(strict=True)
            if not self.book_root_path.is_dir():
                raise NotADirectoryError(
                    f"Provided book_root_path is not a directory: {self.book_root_path}",
                )
        except (FileNotFoundError, NotADirectoryError) as e:
            log.critical(
                "Invalid book_root_path provided to MediaProcessor: %s",
                e,
                exc_info=True,
            )
            raise

        # Build the video domain regex from the configuration.
        if context.config.external_video_domains:
            domains_pattern = "|".join(
                re.escape(d) for d in context.config.external_video_domains
            )
            self.video_domain_rx = re.compile(
                rf"https?://(www\.)?({domains_pattern})/",
                re.IGNORECASE,
            )
        else:
            # Regex that never matches. \b\B is a contradiction: a position that is
            # both a word boundary and not a word boundary.
            self.video_domain_rx = re.compile(r"\b\B")
        # Telemetry counters
        self.handlers: Sequence[BaseMediaHandler] = []
        self.base64_count: int = 0
        self.local_audio_count: int = 0
        self.local_video_count: int = 0
        self.local_image_count: int = 0
        self.external_video_count: int = 0
        self.purged_count: int = 0
        self.error_count: int = 0

    def get_sha256_hash(self, data: bytes) -> str:
        """Computes the SHA-256 hash of binary data for deduplication.

        Args:
            data (bytes): The binary content of the media file.

        Returns:
            str: The hexadecimal representation of the SHA-256 hash.
        """
        return hashlib.sha256(data).hexdigest()

    def get_extension_from_mime(self, mime_type: str) -> str:
        """Derives a file extension from a MIME type string.

        Args:
            mime_type (str): The MIME type, e.g., 'image/png' or 'audio/mpeg'.

        Returns:
            str: The corresponding file extension with a leading dot (e.g., '.png'),
                or an empty string if the type is unknown.
        """
        return MIME_TO_EXTENSION_MAP.get(mime_type.lower(), "")

    def validate_and_resolve_local_asset_path(
        self,
        src_attr: str,
        file_path: Path,
    ) -> Path | None:
        """Validates a media asset path and resolves it to a secure, absolute path.

        Args:
            src_attr (str): The value of the src/data attribute to resolve.
            file_path (Path): The path of the HTML file containing the tag.

        Returns:
            The resolved, absolute Path object if all checks pass, otherwise None.
        """
        if not src_attr or src_attr.startswith(
            ("http://", "https://", "//"),  # NOSONAR
        ):
            return None

        src_path = Path(src_attr)
        if src_path.is_absolute():
            self.handle_local_media_error(
                "Local media path '%s' is absolute. Skipping for security.",
                src_path,
            )
            return None

        ext = normalize_extension(src_path.suffix)
        all_media_ext = AUDIO_EXTENSIONS | VIDEO_EXTENSIONS | IMAGE_EXTENSIONS
        if ext not in all_media_ext:
            return None

        abs_src_path = (file_path.parent / src_path).resolve()

        if not abs_src_path.is_relative_to(self.book_root_path):
            self.handle_local_media_error(
                "Local media path '%s' resolves outside the book root directory. Skipping for security.",
                src_path,
            )
            return None
        if not abs_src_path.is_file():
            self.handle_local_media_error(
                "Local media file not found: %s",
                abs_src_path,
            )
            return None
        return abs_src_path

    def read_local_asset(
        self,
        src_attr: str,
        file_path: Path,
    ) -> tuple[bytes, str] | None:
        """Reads binary data from a local media file path after validation.

        Args:
            src_attr (str): The value of the src/data attribute to read.
            file_path (Path): The path of the current HTML file being processed.

        Returns:
            A tuple of (binary_data, extension) if successful, otherwise None.
        """
        abs_src_path = self.validate_and_resolve_local_asset_path(src_attr, file_path)
        if not abs_src_path:
            return None

        try:
            ext = normalize_extension(abs_src_path.suffix)
            if ext is None:
                self.handle_local_media_error(
                    "Could not determine a valid extension for %s",
                    abs_src_path,
                )
                return None
            return abs_src_path.read_bytes(), ext
        except OSError as e:
            self.handle_local_media_error(
                "Failed to read local media file %s: %s",
                abs_src_path,
                e,
            )
            return None

    def get_media_type_and_increment_counter(self, extension: str) -> str:
        """Determines media type from extension and increments the relevant counter.

        Args:
            extension (str): The file extension (e.g., '.mp3', '.jpg').

        Returns:
            str: The media type ('audio', 'video', or 'images').
        """
        if extension in AUDIO_EXTENSIONS:
            self.local_audio_count += 1
            return "audio"
        if extension in VIDEO_EXTENSIONS:
            self.local_video_count += 1
            return "video"
        self.local_image_count += 1
        return "images"

    def normalize_non_image_tag(
        self,
        tag: Tag,
        soup: BeautifulSoup,
        media_type: str,
        relative_path: str,
    ) -> None:
        """Normalizes a non-image media tag (e.g., <audio>, <video>) in-place.

        Args:
            tag: The original media tag to be replaced.
            soup: The BeautifulSoup object for creating new tags.
            media_type: The type of media ('audio' or 'video').
            relative_path: The new relative path to the media asset.
        """
        new_tag = soup.new_tag(media_type, attrs={"src": relative_path})
        new_tag["controls"] = "controls"
        self.copy_preserved_attributes(tag, new_tag)
        self.preserve_source_and_fallback_children(tag, new_tag, soup, relative_path)
        tag.replace_with(new_tag)

    def create_and_append_source_tag(
        self,
        child: Tag,
        new_tag: Tag,
        soup: BeautifulSoup,
        relative_path: str,
    ) -> None:
        """Creates a new <source> tag from a child and appends it to the new media tag.

        Args:
            child (Tag): The original <source> tag.
            new_tag (Tag): The new parent media tag (<audio> or <video>).
            soup (BeautifulSoup): The BeautifulSoup object for creating new tags.
            relative_path (str): The path to the primary media asset, used as a fallback src.
        """
        source_attrs: dict[str, str] = {
            k: " ".join(v) if isinstance(v, list) else str(v)
            for k, v in child.attrs.items()
            if v is not None
        }
        if "src" not in source_attrs:
            source_attrs["src"] = relative_path
        new_source = soup.new_tag("source", attrs=source_attrs)
        new_tag.append(new_source)

    def preserve_source_and_fallback_children(
        self,
        original_tag: Tag,
        new_tag: Tag,
        soup: BeautifulSoup,
        relative_path: str,
    ) -> None:
        """Preserves <source> and other children from an old tag to a new one.

        Args:
            original_tag: The original media tag.
            new_tag: The new media tag to which children will be appended.
            soup: The BeautifulSoup object for creating new tags.
            relative_path: The path to the primary media asset.
        """
        if not (children := snapshot_iterator(original_tag.children)):
            new_tag.string = f"Embedded {new_tag.name}"
            return

        for child in children:
            if isinstance(child, Tag) and child.name == "source":
                self.create_and_append_source_tag(child, new_tag, soup, relative_path)
            else:
                new_tag.append(child)

    def handle_local_media_error(self, message_format: str, *format_args: Any) -> None:
        """Logs a media processing error and increments the error counter.

        Args:
            message_format (str): The warning message format string.
            *format_args (Any): The arguments to be formatted into the message.
        """
        log.warning(message_format, *format_args)
        self.error_count += 1

    def save_asset_to_sibling_dir(
        self,
        media_type: str,
        asset_filename: str,
        binary_data: bytes,
    ) -> str:
        """Saves binary data to a subdirectory within the sibling asset directory.

        Args:
            media_type: The subdirectory name (e.g., 'images', 'extracted').
            asset_filename: The target filename for the asset.
            binary_data: The binary content to write.

        Returns:
            The relative path to the saved asset.
        """
        output_dir = self.sibling_asset_dir / media_type
        relative_path = posixpath.join(media_type, asset_filename)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / asset_filename
        if not output_path.exists():
            output_path.write_bytes(binary_data)
        return relative_path

    def merge_classes(self, src_value: Any, dest_tag: Tag) -> None:
        """Merges 'class' attributes from a source to a destination tag.

        Args:
            src_value (Any): The raw 'class' attribute value from the source tag.
            dest_tag (Tag): The destination tag whose 'class' attribute will be modified.
        """
        src_classes = coerce_class_list(src_value)
        dest_classes = coerce_class_list(dest_tag.get("class", None))

        merged_classes = dest_classes[:]
        for class_name in src_classes:
            if class_name not in merged_classes:
                merged_classes.append(class_name)

        if merged_classes:
            dest_tag["class"] = " ".join(merged_classes)

    def copy_preserved_attributes(self, src_tag: Tag, dest_tag: Tag) -> None:
        """Copies preserved semantic attributes from one tag to another.

        Args:
            src_tag (Tag): The source tag to copy attributes from.
            dest_tag (Tag): The destination tag to copy attributes to.
        """
        attrs_to_preserve = {
            "id",
            "class",
            "style",
            "title",
            "role",
            "lang",
            "width",
            "height",
        }

        for attr, value in src_tag.attrs.items():
            if attr in attrs_to_preserve or attr.startswith(("aria-", "data-")):
                if attr == "class":
                    self.merge_classes(value, dest_tag)
                else:
                    dest_tag[attr] = value

    def create_video_placeholder_img(self, tag: Tag, soup: BeautifulSoup) -> Tag:
        """Creates a placeholder <img> tag for a video, preserving alt text and dimensions.

        Args:
            tag (Tag): The original media tag.
            soup (BeautifulSoup): The BeautifulSoup object.

        Returns:
            Tag: The new placeholder <img> tag.
        """
        raw_img_attrs: dict[str, Any] = {
            "alt": tag.get("alt") or tag.get("title") or "External video content",
            "src": "placeholder.png",
        }
        for size_attr in ("width", "height"):
            if size_attr in tag.attrs:
                raw_img_attrs[size_attr] = tag[size_attr]

        final_img_attrs: dict[str, str] = {}
        for key, value in raw_img_attrs.items():
            if value is None:
                continue
            if isinstance(value, list):
                final_img_attrs[key] = str(value[0]) if value else ""
            else:
                final_img_attrs[key] = str(value)

        return soup.new_tag("img", attrs=final_img_attrs)

    def process(
        self,
        soup: BeautifulSoup,
        file_path: Path,
    ) -> tuple[BeautifulSoup, Mapping[str, Any]]:
        """Executes the full multimedia extraction and normalization pipeline.

        Args:
            soup (BeautifulSoup): The in-memory DOM of the document to be processed.
            file_path (Path): The path to the current HTML file, needed to resolve
                relative media paths.

        Returns:
            A tuple containing the mutated soup object and a metadata dictionary.
        """
        self.handlers = get_media_handlers(self)

        target_tags = [
            "img",
            "image",
            "audio",
            "video",
            "iframe",
            "embed",
            "object",
            "script",
            "canvas",
        ]

        for tag in find_all_snapshot(soup, target_tags):
            if not isinstance(tag, Tag):
                continue
            if self.context.is_inside_code_block(tag):
                continue

            for handler in self.handlers:
                if handler.can_handle(tag):
                    handler.handle(tag, soup, file_path)
                    break

        has_changes = (
            self.base64_count > 0
            or self.local_audio_count > 0
            or self.local_video_count > 0
            or self.local_image_count > 0
            or self.external_video_count > 0
            or self.purged_count > 0
        )

        if self.error_count > 0:
            status = PipelineStatus.ERROR
        elif has_changes:
            status = PipelineStatus.SUCCESS
        else:
            status = PipelineStatus.SUCCESS_NOOP

        metadata = generate_processor_metadata(
            processor_key="media_processing",
            status=status,
            base64_images_extracted=self.base64_count,
            local_audio_files_mapped=self.local_audio_count,
            local_video_files_mapped=self.local_video_count,
            local_image_files_mapped=self.local_image_count,
            external_videos_wrapped=self.external_video_count,
            unsupported_media_purged=self.purged_count,
            media_processing_errors=self.error_count,
        )
        return soup, metadata
