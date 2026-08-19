"""Identifies prose quotations based on consistent typographic indentation."""

from __future__ import annotations

import logging
import re

from bs4 import BeautifulSoup, Tag

from ..core import BookStyleContext
from ..core.dom_utils import normalize_style_attribute
from .base_strategy import PROCESSOR_UNBOUND_MSG, BaseBlockquoteStrategy

log = logging.getLogger(__name__)


class ProseQuoteStrategy(BaseBlockquoteStrategy):
    """Identifies prose quotations based on consistent typographic indentation.

    This is the third-priority strategy (Priority 3). It detects blocks of text
    that are visually set apart from the main narrative by a consistent left
    indentation, a common method for formatting blockquotes in prose.
    """

    def _strip_indent_style(self, node: Tag) -> None:
        """Removes the style attribute from a node unconditionally.

        This method completely removes the `style` attribute from the node,
        discarding all inline styles, to enforce a clean semantic structure
        within the blockquote.
        """
        if "style" in node.attrs:
            del node["style"]
            log.debug(
                "Unconditionally stripped style attribute from node: %r",
                node,
            )

    def _parse_indent_style(self, style_str: str) -> tuple[float, str] | None:
        """Parses indentation style from a style string.

        Returns:
            A tuple of (value, unit) if a valid indent is found, otherwise None.

        Notes:
            - Negative or zero values are rejected as non-semantic layout tweaks.
        """
        # Match a single margin-left or padding-left declaration with a numeric
        # value and unit, allowing optional whitespace and trailing content.
        # Use a case-insensitive regex and find the last match to respect CSS order.
        # The numeric pattern is restricted to valid integers/decimals to avoid
        # malformed values like "1.2.3" or "...5", so error handling is reserved
        # for truly unexpected input rather than loose parsing.
        log.debug("Parsing indent style from: '%s'", style_str)
        matches = list(
            re.finditer(
                # Use a negative lookahead to ensure the unit is not part of a larger word,
                # which is more robust than `\b` for non-alphanumeric units like '%'.
                r"(?:^|;)\s*(margin|padding)-left\s*:\s*(-?(?:\d*\.\d+|\d+))(em|rem|px|pt|cm|%)(?![a-z0-9])",
                style_str,
                flags=re.IGNORECASE,
            ),
        )
        if not matches:
            log.debug("No margin/padding-left declaration found.")
            return None

        # Respect CSS order: last declaration wins
        _prop, value_str, unit_str = matches[-1].groups()
        log.debug("Found potential indent: %s %s", value_str, unit_str)
        try:
            value = float(value_str)
        except ValueError:
            log.warning("Could not parse indent value '%s' as float.", value_str)
            return None

        # Reject negative/zero indentation values as non-semantic layout tweaks.
        if value <= 0:
            log.debug("Rejecting non-positive indent value: %f", value)
            return None

        unit = unit_str.lower()
        log.debug("Parsed indent successfully: (%f, '%s')", value, unit)
        return value, unit

    def find_and_apply(
        self,
        start_node: Tag,
        context: BookStyleContext,
        soup: BeautifulSoup,
    ) -> list[Tag] | None:
        """Finds and applies the prose quote strategy (Priority 3).

        This method identifies prose quotations based on consistent text
        indentation styles. If a valid sequence is found, it is wrapped in a
        `<blockquote>`, the indentation styles are stripped, and the list of
        processed nodes is returned.

        Mutations:
            - Wraps the identified prose nodes in a new `<blockquote>` element.
            - Strips the `margin-left` or `padding-left` inline style properties
              from the wrapped nodes.

        Rules & Limits:
            - This is the third priority strategy (Priority 3).
            - Full depth traversal: Yes.
        """
        log.debug("ProseQuoteStrategy: Checking node: %r", start_node)
        sequence = self._collect_sequence(start_node)
        if not sequence:
            log.debug("ProseQuoteStrategy: No sequence collected. Skipping.")
            return None

        log.debug("ProseQuoteStrategy: Collected sequence of %d nodes.", len(sequence))
        if not self._is_candidate_valid(sequence):
            log.debug("ProseQuoteStrategy: Candidate sequence is not valid. Skipping.")
            return None

        log.debug("ProseQuoteStrategy: Candidate is valid. Wrapping nodes.")
        self._wrap_nodes_in_blockquote(sequence, soup)
        for node in sequence:
            self._strip_indent_style(node)

        assert self.processor, PROCESSOR_UNBOUND_MSG
        self.processor.generic_quotes_created_count += 1
        log.debug(
            "ProseQuoteStrategy: Finished. Returning sequence of %d.",
            len(sequence),
        )
        return sequence

    def _is_candidate_valid(self, nodes: list[Tag]) -> bool:
        """Applies validation filters suitable for prose, skipping the TTR check.

        This override bypasses the Text-to-Tag Ratio (TTR) filter from the
        base class, which can be too aggressive for short prose quotes. It
        retains the anchor density filter to prevent navigation menus from being
        misidentified as prose quotes by reusing the base implementation.

        Args:
            nodes: A list of candidate `Tag` objects forming a potential
                blockquote.

        Returns:
            True if the candidate passes the anchor density filter, False otherwise.
        """
        if not nodes:
            return False

        # We cannot call super()._is_candidate_valid() because we need to skip
        # the TTR check. Instead, we call the specific validation helpers we need.
        stats = self._get_content_stats(nodes)

        return self._is_anchor_density_valid(
            stats["anchor_chars"],
            stats["total_chars"],
        )

    def _get_valid_indent_tuple(self, node: Tag) -> tuple[float, str] | None:
        """Checks if a node has a significant indentation style.

        Args:
            node (Tag): The node to inspect for indentation styles.

        Returns:
            A tuple of (value, unit) if a valid indent is found, otherwise None.

        Mutations:
            None.

        Rules & Limits:
            - Target Properties: Checks for `margin-left` or `padding-left` in the
              node's `style` attribute.
            - Thresholds: The style value must be a numerical value greater than
              or equal to 1.5em or 20px.
            - Node Type Safety: Expects `node` to be a `Tag`. Will return `None`
              if the `style` attribute is missing or the node is not a `Tag`.
        """
        style_attr = node.get("style")
        if not style_attr:
            return None
        style_str = normalize_style_attribute(style_attr)

        parsed_indent = self._parse_indent_style(style_str)
        if not parsed_indent:
            return None

        value, unit = parsed_indent

        assert self.config is not None, "Config not bound to strategy"
        thresholds = {
            "em": self.config.prose_quote_min_indent_em,
            "rem": self.config.prose_quote_min_indent_em,
            "px": self.config.prose_quote_min_indent_px,
            "%": self.config.prose_quote_min_indent_percent,
            "pt": self.config.prose_quote_min_indent_pt,
            "cm": self.config.prose_quote_min_indent_cm,
        }

        min_value = thresholds.get(unit)

        # Check if the unit is supported and the value meets the threshold.
        if min_value is not None and value >= min_value:
            log.debug(
                "Indent (%f, '%s') is valid for node: %r",
                value,
                unit,
                node,
            )
            return value, unit

        log.debug(
            "Indent (%f, '%s') is below threshold for node: %r",
            value,
            unit,
            node,
        )
        return None

    def _collect_sequence(
        self,
        start_node: Tag,
    ) -> list[Tag] | None:
        """Collects a sequence of contiguous sibling nodes with the same indent.

        Args:
            start_node (Tag): The first node in the sequence.

        Returns:
            A list of `Tag` objects forming the indented sequence, or `None`.

        Rules & Limits:
            - Homogeneity: Collects consecutive sibling paragraphs that have any
              valid indentation, as determined by `_get_valid_indent_tuple`.
            - Sibling Traversal: Safely traverses `previous_sibling` and
              `next_sibling` to find the full sequence.
        """
        if start_node.name not in {"p", "div"} or not self._get_valid_indent_tuple(
            start_node,
        ):
            return None

        # Pass 1: Find the true start of the sequence by traversing backwards.
        first_node_in_sequence = start_node
        node_iterator = start_node
        while True:
            prev_sibling = self._get_prev_non_ignorable_sibling(node_iterator)
            if (prev_sibling
                and prev_sibling.name in {"p", "div"}
                and self._get_valid_indent_tuple(prev_sibling)
            ):
                first_node_in_sequence = prev_sibling
                node_iterator = prev_sibling
            else:
                break

        # Pass 2: Collect all contiguous, valid nodes forwards from the start.
        sequence = []
        node_iterator = first_node_in_sequence
        while (
            node_iterator
            and node_iterator.name in {"p", "div"}
            and self._get_valid_indent_tuple(node_iterator)
        ):
            sequence.append(node_iterator)
            node_iterator = self._get_next_non_ignorable_sibling(node_iterator)

        return sequence
