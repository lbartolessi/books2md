"""Helper module for poetry indentation and stanza break detection heuristics.

This module centralizes the logic for calculating indentation levels from CSS
styles and non-breaking spaces, as well as determining if a DOM node contains
renderable text for stanza break detection.
"""

from __future__ import annotations

import re
from typing import Final

from bs4.element import NavigableString, PageElement, Tag

from ..core import BookStyleContext
from ..core.dom_utils import normalize_style_attribute

# Matches only standard ASCII whitespace characters: space, tab, newline,
# carriage return, form feed, and vertical tab. Does not match NBSP (\xa0).
_STANDARD_WHITESPACE_PATTERN_RX: Final[re.Pattern[str]] = re.compile(r"[ \t\n\r\f\v]+")


class PoetryIndentationHelper:
    """Helper for calculating indentation and detecting renderable text in poetry blocks."""

    def __init__(self, context: BookStyleContext):
        """Initializes the helper with configuration for indentation and heuristics.

        Args:
            context (BookStyleContext): The shared context for the book, providing
                access to configuration.
        """
        self.context = context
        self.em_to_indent_ratio = context.config.poetry_em_to_indent_ratio
        self.px_to_em_ratio = context.config.poetry_px_to_em_ratio
        self.percent_to_indent_ratio = context.config.poetry_percent_to_indent_ratio
        self.nbsp_to_indent_ratio = context.config.poetry_nbsp_to_indent_ratio
        self.max_nbsp_depth = context.config.poetry_max_nbsp_depth
        self.indentation_tag_whitelist = context.config.poetry_indentation_tag_whitelist
        self.indentation_properties = context.config.poetry_indentation_properties
        self.indentation_units = context.config.poetry_indentation_units

        props_group = "|".join(re.escape(p) for p in self.indentation_properties)
        units_group = "|".join(re.escape(u) for u in self.indentation_units)

        self._indent_pattern_rx: Final[re.Pattern[str]] = re.compile(
            fr"""
            (?P<prop>{props_group})   # property name
            \s*:\s*                                           # optional whitespace around colon
            (?P<value>[+-]?\d+(?:\.\d*)?)                     # numeric value (int or float)
            \s*(?P<unit>{units_group})                          # unit
            """,
            re.IGNORECASE | re.VERBOSE,
        )

    def _parse_indent_from_style(self, style_str: str) -> int:
        """Parses a style string and calculates a cumulative indent level.

        Args:
            style_str (str): The CSS style string to parse.

        Returns:
            int: The calculated indentation level from CSS properties.
        """
        indent = 0
        for declaration in style_str.split(";"):
            if not (declaration := declaration.strip()):
                continue

            if not (match := self._indent_pattern_rx.search(declaration)):
                continue

            val_str = match.group("value")
            unit = match.group("unit").lower()
            try:
                val = float(val_str)
            except ValueError:
                continue  # Skip malformed numeric values

            if unit in ("em", "rem"):
                indent += int(val * self.em_to_indent_ratio)
            elif unit == "px":
                indent += int(val * self.px_to_em_ratio)
            elif unit == "%":
                indent += int(val * self.percent_to_indent_ratio)
        return indent

    def _calculate_indent_from_nbsp(self, line_node: Tag) -> int:
        """Calculates indent level from leading non-breaking spaces.

        Args:
            line_node (Tag): The node representing the line.

        Returns:
            int: The calculated indentation level from leading non-breaking spaces.
        """
        # Build text only from direct child text nodes (not descendants) so that
        # indentation is determined solely by the line node's own leading text,
        # and not by nested inline elements.
        #
        # We still avoid normalization by accessing `str` directly from
        # NavigableString instances, which preserves non-breaking spaces.
        direct_text_chunks: list[str] = []
        for child in line_node.contents:
            # Only consider direct text nodes; skip nested tags.
            if isinstance(
                child, NavigableString
            ):  # pyright: ignore[reportUnnecessaryIsInstance]
                direct_text_chunks.append(str(child))
            else:
                # Once we encounter the first non-text child, we stop collecting
                # further direct text for indentation purposes, since indentation
                # should come from leading text only.
                break

        text = "".join(direct_text_chunks)

        # Skip leading regular spaces/tabs to find the first potentially
        # indentation-relevant character.
        first_non_space_tab_idx = 0
        while first_non_space_tab_idx < len(text) and text[first_non_space_tab_idx] in (
            " ",
            "\t",
        ):
            first_non_space_tab_idx += 1

        # From that position, count contiguous NBSPs only. This avoids
        # miscounting when NBSPs are interleaved with other whitespace
        # or characters, e.g. "\u00a0 \u00a0text".
        nbsp_count = 0
        idx = first_non_space_tab_idx
        while idx < len(text) and text[idx] == "\u00a0":
            nbsp_count += 1
            idx += 1

        return int(nbsp_count * self.nbsp_to_indent_ratio) if nbsp_count else 0

    def calculate_indent(self, line_node: Tag) -> int:
        """Calculates a numeric indent level from styles and non-breaking spaces.

        Args:
            line_node (Tag): The node representing the line.

        Returns:
            int: The total calculated indentation level.
        """
        indent = 0
        style = normalize_style_attribute(line_node.get("style"))

        if style:
            indent += self._parse_indent_from_style(style)

        indent += self._calculate_indent_from_nbsp(line_node)
        return indent

    def is_indentation_only_line(self, node: Tag) -> bool:
        """Checks if a tag represents an indentation-only line via NBSPs.

        An indentation-only line is defined as a line that contains at least one
        non-breaking space (`&nbsp;`) and no other non-whitespace characters.
        This heuristic is constrained by depth and tag type to avoid
        over-classifying layout noise as stanza content.

        Args:
            node: The BeautifulSoup Tag to evaluate.

        Returns:
            True if the node is an indentation-only line, False otherwise.
        """
        depth = self._compute_dom_depth(node)
        if (
            depth > self.max_nbsp_depth
            or node.name not in self.indentation_tag_whitelist
        ):
            return False

        text = "".join(node.strings)

        # An indentation-only line must contain at least one non-breaking space
        # and must become an empty string after stripping all standard whitespace
        # (spaces, tabs, newlines) while preserving non-breaking spaces.
        # This avoids relying on the default str.strip() behavior for \u00a0 and
        # instead makes the normalization step explicit.
        normalized_text = _STANDARD_WHITESPACE_PATTERN_RX.sub("", text)
        return "\u00a0" in text and not normalized_text

    def node_has_renderable_text(self, node: PageElement) -> bool:
        """Checks if a node has any renderable text content.

        Renderable content is defined as any sequence of characters that is not
        exclusively composed of standard whitespace (spaces, tabs, newlines).
        Non-breaking spaces (`&nbsp;`) are considered renderable content.

        Args:
            node (PageElement): The node to check.

        Returns:
            bool: True if the node has renderable text content, False otherwise.
        """
        if isinstance(node, Tag) and node.name == "br":
            return False

        # For NavigableString, just convert to string. For Tags, get all text.
        text = str(node) if isinstance(node, NavigableString) else node.get_text()

        # Standard .strip() or `\s` in regex incorrectly removes non-breaking
        # spaces (`\xa0`). We must use a specific regex to remove only
        # standard whitespace characters.
        text_without_standard_whitespace = _STANDARD_WHITESPACE_PATTERN_RX.sub("", text)
        return bool(text_without_standard_whitespace)

    @staticmethod
    def _compute_dom_depth(tag: Tag) -> int:
        """Computes the DOM depth of a tag from its parent."""
        depth = 0
        parent = tag.parent
        while parent is not None and isinstance(parent, Tag): # pyright: ignore[reportUnnecessaryIsInstance]
            depth += 1
            parent = parent.parent
        return depth
