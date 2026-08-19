"""
A collection of robust, stateless utility functions for DOM analysis and mutation.

This module provides a centralized toolkit of helper functions that are used
across multiple normalizer modules. These utilities are designed to be pure and have
no dependencies on the specific state of any processor, ensuring they are reusable
and testable in isolation.
"""

import re
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any, Final, cast

from bs4 import BeautifulSoup
from bs4.element import NavigableString, PageElement, Tag

from .config import EngineConfiguration
from .constants import PAGE_MARKER_RX
from .status import PipelineStatus

# A translation table for `str.translate` to efficiently replace special
# whitespace characters with a standard space.
_WHITESPACE_TRANSLATION_TABLE: Final[dict[int, str]] = str.maketrans(
    {
        "\xa0": " ",  # Non-breaking space
        "\u200b": " ",  # Zero-width space
        "\u202f": " ",  # Narrow non-breaking space
        "\ufeff": " ",  # Byte Order Mark (can act as a zero-width space)
    },
)

# Reserved keys for the metadata payload that cannot be passed in `**metrics`.
_RESERVED_METADATA_KEYS: Final[frozenset[str]] = frozenset(
    {"execution_timestamp", "status"},
)


def _is_page_marker_pattern(cleaned_text: str) -> bool:
    """Checks if a pre-cleaned, non-empty string matches the page marker regex.

    Args:
        cleaned_text (str): The text to check, already stripped and normalized.

    Returns:
        bool: True if the text matches the page marker pattern, False otherwise.
    """
    return bool(PAGE_MARKER_RX.fullmatch(cleaned_text))


def is_page_marker_noise(text: str | None) -> bool:
    """Evaluates if a text string is a non-semantic pagination marker.

    This function is robust against various whitespace, including non-breaking
    spaces, as it normalizes the input before matching.

    Args:
        text: The content to evaluate. This should be the raw node text; any
            whitespace normalization is handled internally.

    Returns:
        True if the text matches the page marker pattern.
    """
    if not text:
        return False
    cleaned_text = normalize_whitespace(text)
    return _is_page_marker_pattern(cleaned_text)


def _has_semantic_attributes(node: Tag, config: EngineConfiguration) -> bool:
    """Checks if a tag has attributes that are considered semantically significant.

    This helper intentionally treats any attribute starting with the configured
    semantic prefixes (currently all ``aria-*`` and ``data-*`` attributes), as
    well as explicitly listed attribute names, as semantically significant. The
    classification is deliberately broad so that nodes with potentially meaningful
    metadata are not discarded, even if the attribute name is application-specific.

    Args:
        node: The BeautifulSoup Tag to inspect.

    Returns:
        True if the node has any attributes matching the semantic lists or prefixes,
        False otherwise.

    Raises:
        None

    Mutations:
        None
    """
    return any(
        attr in config.semantic_attrs
        # Efficiently check if the attribute starts with any of the semantic prefixes.
        or attr.startswith(config.semantic_attr_prefixes)
        for attr in node.attrs
    )


def is_ignorable_node(node: PageElement | str | None, config: EngineConfiguration) -> bool:
    """Evaluates if a node is ignorable structural or whitespace noise.

    An ignorable node has no renderable content. This includes `None`, whitespace-only
    text nodes, `<br>` tags, and tags that are empty or contain only a page marker.
    Media tags (like `<img>`) are always considered renderable content and are never
    ignorable.

    Note:
        "Renderable content" is strictly defined as non-whitespace text or a tag from
        the `_MEDIA_TAGS` set. Tags with semantically significant attributes (like
        `role` or `aria-*`) are also considered non-ignorable, as they carry
        meaning beyond their visible content.

    Args:
        node: The BeautifulSoup node or other object to evaluate.

    Returns:
        True if the node is considered ignorable, False otherwise.

    Raises:
        None

    Mutations:
        None
    """
    # Handle string-like objects (NavigableString and str)
    if isinstance(node, (NavigableString, str)):
        normalized_text = normalize_whitespace(str(node))
        return not normalized_text or _is_page_marker_pattern(normalized_text)

    # Handle BeautifulSoup Tags. `elif node:` is not specific enough for type
    # checkers when the input can be a generic PageElement.
    elif isinstance(node, Tag):
        if node.name == "br": # pyright: ignore[reportUnnecessaryComparison]
            return True

        if ( # pyright: ignore[reportUnnecessaryComparison]
            node.name in config.media_tags
            or _has_semantic_attributes(node, config)
            or node.find(lambda tag: tag.name in config.media_tags)
        ):
            return False

        normalized_text = normalize_whitespace(node.get_text())
        return not normalized_text or _is_page_marker_pattern(normalized_text)

    # For any other type, only None is considered ignorable.
    return node is None


def normalize_whitespace(text: str | None) -> str:
    """Collapses all whitespace sequences and special whitespace characters.

    This function performs a three-step normalization:
    1.  Replaces specific Unicode characters (like non-breaking spaces) with a
        standard space using an efficient translation table. This ensures that
        visually similar or invisible characters are handled consistently.
    2.  Collapses any sequence of one or more whitespace characters (now including
        the replaced ones) into a single standard space using a regex.
    3.  Strips any leading or trailing whitespace from the final string.

    Args:
        text (str | None): The input string to normalize.

    Returns:
        str: The normalized string.
    """
    if not text:
        return ""
    # 1. Replace special whitespace characters using a pre-compiled translation table.
    # This is more efficient than chained .replace() calls.
    text = text.translate(_WHITESPACE_TRANSLATION_TABLE)
    # 2. Collapse all general whitespace sequences into a single space.
    text = re.sub(r"\s+", " ", text)
    # 3. Strip leading/trailing whitespace.
    return text.strip()


def get_utc_timestamp() -> str:
    """Generates a canonical ISO 8601 UTC timestamp string.

    Args:
        None

    Returns:
        str: The formatted timestamp string."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def snapshot_iterator(iterator: Iterable[PageElement]) -> tuple[PageElement, ...]:
    """Creates a static snapshot of a BeautifulSoup iterator for safe mutation.

    This is a crucial utility for safe DOM mutation. Iterating directly over a
    live iterator from methods like `find_all` or `.children` can lead to
    unpredictable behavior if the DOM is modified within the loop (e.g., via
    `replace_with` or `unwrap`). This function consumes the entire iterator
    and returns an immutable tuple, ensuring the loop's target sequence is
    fixed before any mutations begin.

    Args:
        iterator: A BeautifulSoup iterator (e.g., from `soup.find_all(...)`).

    Returns:
        A tuple of the elements from the iterator.

    Raises:
        None

    Mutations:
        None
    """
    return tuple(iterator)


def find_all_snapshot(
    soup: BeautifulSoup | Tag,
    *args: Any,
    **kwargs: Any,
) -> tuple[PageElement, ...]:
    """Finds all matching elements and returns them as a static tuple for safe mutation.

    This is a convenience wrapper around `snapshot_iterator(soup.find_all(...))`
    to reduce verbosity and make the safe iteration pattern more explicit.

    Args:
        soup: The BeautifulSoup or Tag object to search within.
        *args: Positional arguments passed to `find_all`.
        **kwargs: Keyword arguments passed to `find_all`.

    Returns:
        A tuple of the found elements.

    Raises:
        None

    Mutations:
        None
    """
    return snapshot_iterator(soup.find_all(*args, **kwargs))


def select_snapshot(
    soup: BeautifulSoup | Tag,
    selector: str,
    **kwargs: Any,
) -> tuple[PageElement, ...]:
    """Selects all matching elements using a CSS selector and returns a static tuple.

    This is a convenience wrapper around `snapshot_iterator(soup.select(...))`
    to reduce verbosity and make the safe iteration pattern more explicit.

    Args:
        soup: The BeautifulSoup or Tag object to search within.
        selector: A CSS selector string.
        **kwargs: Keyword arguments passed to `select` (e.g., `limit`).

    Returns:
        A tuple of the found elements.

    Raises:
        None

    Mutations:
        None
    """
    return snapshot_iterator(soup.select(selector, **kwargs))


def coerce_class_list(class_attr: str | list[str] | None) -> list[str]:
    """Normalizes a 'class' attribute into a deduplicated list of strings.

    This safely handles `class` attributes that are strings, lists, or None,
    producing a consistent, mutable list of unique class names while preserving
    their original order.

    Args:
        class_attr: The raw value from a node's `get('class')` call.

    Returns:
        A deduplicated list of class name strings.

    Raises:
        None

    Mutations:
        None
    """
    if not class_attr:
        return []

    initial_list: list[str]
    if isinstance(class_attr, str):  # pyright: ignore[reportUnnecessaryIsInstance]
        initial_list = class_attr.strip().split()
    elif isinstance(
        class_attr, list
    ):  # pyright: ignore[reportUnnecessaryIsInstance]
        # Filter to string items, strip them, and remove any empty results.
        initial_list = [s.strip() for s in class_attr if s.strip()]
    else:
        return []

    # Return a deduplicated list while preserving order.
    return list(dict.fromkeys(initial_list))


def normalize_style_attribute(style_attr: Any) -> str:
    """Normalizes a raw style attribute into a clean string.

    Handles cases where the style attribute might be a list of strings or
    None, returning a single, stripped string for reliable processing.

    Args:
        style_attr: The raw `style` attribute value from a BeautifulSoup tag.

    Returns:
        A clean, stripped string representation of the style, or an empty
        string if the attribute is missing or empty.
    """
    if not style_attr:
        return ""
    if isinstance(style_attr, list):
        return " ".join(style_attr).strip()
    return str(style_attr).strip()


def strip_css_properties(
    style_str: str,
    props_to_remove: frozenset[str],
) -> str:
    """Removes a set of CSS properties from an inline style string.

    Args:
        style_str: The inline style string (e.g., "color: red; font-size: 12px;").
        props_to_remove: A set of lowercase property names to remove.

    Returns:
        A new style string with the specified properties removed. If all
        properties are removed, an empty string is returned.

    Raises:
        None

    Mutations:
        None
    """
    if not style_str:
        return ""

    declarations = [d.strip() for d in style_str.split(";") if d.strip()]
    kept_declarations = []
    for decl in declarations:
        if ":" in decl:
            prop, _ = decl.split(":", 1)
            if prop.strip().lower() not in props_to_remove:
                kept_declarations.append(decl)

    return f"{'; '.join(kept_declarations)};" if kept_declarations else ""


def clone_tag(tag: Tag) -> Tag:
    """Creates a deep copy of a BeautifulSoup Tag.

    This utility provides a reliable method for creating a deep copy of a tag that
    is completely detached from its original document. It uses BeautifulSoup's
    string-reparsing mechanism, which is the only fully supported way to achieve
    a deep copy. The new tag is parsed using the same builder (e.g., 'html5lib',
    'html.parser') as the original tag's document to ensure consistency. If the
    tag is not associated with a document, it defaults to 'html.parser'.

    Note:
        This operation can be a performance bottleneck for very large or complex
        tags due to the overhead of serializing the tag to a string and then
        re-parsing it. It should be used judiciously, particularly in loops
        processing many large elements.

    Args:
        tag: The BeautifulSoup Tag to clone.

    Returns:
        A new Tag object that is a deep copy of the original.
    """
    # The `tag.builder` attribute correctly references the builder from the
    # original soup object. If the tag is detached, `tag.builder` can be None,
    # so we fall back to the default 'html.parser' to prevent an error.
    # Pylance can sometimes incorrectly infer the type of `tag.builder.NAME`.
    # We use an explicit cast to `str` to ensure `parser_name` is correctly
    # typed and resolve the false positive from the type checker.
    parser_name = cast(str, tag.builder.NAME) if tag.builder else "html5lib"
    return cast(
        Tag,
        BeautifulSoup(str(tag), parser_name).contents[0],
    )


def get_tag_identifier(tag: Tag, attr_value_limit: int) -> str:
    """Creates a simple, readable, and truncated identifier for a tag for logging.

    This keeps anomaly logs and other reporting compact and safe by preventing
    excessively long or sensitive attribute values from being recorded verbatim.

    Args:
        tag: The BeautifulSoup Tag to identify.
        attr_value_limit: The maximum length for attribute values before truncation.

    Returns:
        A string representation of the tag, like `<p class="foo...">`, with
        long attribute values truncated.
    """
    attr_parts = []
    for k, v_raw in tag.attrs.items():
        v_str = " ".join(v_raw) if isinstance(v_raw, list) else str(v_raw)
        if len(v_str) > attr_value_limit:
            v_str = f"{v_str[:attr_value_limit]}..."
        attr_parts.append(f'{k}="{v_str}"')
    attrs_str = f" {' '.join(attr_parts)}" if attr_parts else ""
    return f"<{tag.name}{attrs_str}>"


def generate_processor_metadata(
    processor_key: str,
    status: PipelineStatus,
    *,
    execution_timestamp: str | None = None,
    **metrics: Any,
) -> dict[str, Any]:
    """Constructs a standardized metadata dictionary for a pipeline stage.

    Args:
        processor_key: The top-level key for the metadata dictionary.
        status: The final status of the pipeline run.
        execution_timestamp: An optional ISO 8601 timestamp. If not provided,
            the current UTC time is generated. This is useful for creating
            deterministic output for tests.
        **metrics: Additional key-value pairs to include in the payload. These
            must not include the reserved keys 'status' or 'execution_timestamp'.

    Returns:
        A dictionary with the structured metadata. By convention, callers
        should treat this as a read-only object.

    Raises:
        ValueError: If `metrics` contains any of the reserved keys.

    Mutations:
        None
    """
    if conflicting_keys := _RESERVED_METADATA_KEYS.intersection(metrics.keys()):
        raise ValueError(
            f"Processor '{processor_key}' provided a metrics dictionary that "
            f"contains reserved keys: {', '.join(sorted(conflicting_keys))}",
        )

    payload = {
        **metrics,
        "execution_timestamp": execution_timestamp or get_utc_timestamp(),
        "status": status.value,
    }
    return {processor_key: payload}
