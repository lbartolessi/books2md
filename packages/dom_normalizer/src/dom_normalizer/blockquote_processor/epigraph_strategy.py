"""Identifies epigraphs based on typography and proximity to headings."""

from __future__ import annotations

import logging
from enum import Enum, auto

from bs4 import BeautifulSoup, Tag

from dom_normalizer.core.dom_utils import is_ignorable_node, normalize_style_attribute

from ..core import BookStyleContext
from .base_strategy import PROCESSOR_UNBOUND_MSG, BaseBlockquoteStrategy

log = logging.getLogger(__name__)


class SiblingStatus(Enum):
    """Represents the role of a sibling node in epigraph detection."""

    HEADING = auto()
    BLOCKER = auto()
    NEITHER = auto()


class EpigraphStrategy(BaseBlockquoteStrategy):
    """Identifies epigraphs based on typography and proximity to headings.

    This is the highest-priority strategy (Priority 1). It looks for short,
    right-aligned paragraphs that appear immediately after a chapter or section
    heading, a common typographic pattern for introductory quotes.
    """

    def _get_style_property(self, node: Tag, property_name: str) -> str | None:
        """Parses the style attribute of a node and returns the value of a given CSS property.

        Args:
            node: The BeautifulSoup Tag to inspect.
            property_name: The name of the CSS property to find (e.g., 'text-align').

        Returns:
            The value of the property if found, otherwise None. The search is
            case-insensitive, and the value is returned in lowercase.
        """
        style_attr = node.get("style")
        if not style_attr:
            return None

        style_str = normalize_style_attribute(style_attr)
        for decl in reversed(style_str.split(";")):
            stripped_decl = decl.strip()
            if not stripped_decl:
                continue
            if ":" in stripped_decl:
                prop, value = stripped_decl.split(":", 1)
                if prop.strip().lower() == property_name.lower():
                    return value.strip().lower()
        return None

    def _has_right_align_style(self, node: Tag) -> bool:
        """Checks if the node has a 'text-align: right' style."""
        text_align_value = self._get_style_property(node, "text-align")
        return text_align_value == "right"

    def _is_within_max_length(self, node: Tag) -> bool:
        """Checks if the node's text content is within the max length."""
        assert self.config is not None, "Config not bound to strategy"
        return len(node.get_text(strip=True)) <= self.config.epigraph_max_length

    def _get_sibling_status(self, node: Tag) -> SiblingStatus:
        """Determines if a node is a heading, a blocking element, or neither.

        Any heading immediately preceding a candidate quote is a potential
        epigraph header. Any "substantial" intervening content between a
        heading and a quote (as defined by BLOCKING_TAGS) invalidates the
        epigraph.
        """
        name = (node.name or "").lower()
        assert self.config is not None, "Config not bound to strategy"

        if name in self.config.epigraph_heading_tags:
            return SiblingStatus.HEADING

        if name in self.config.epigraph_blocking_tags:
            return SiblingStatus.BLOCKER

        return SiblingStatus.NEITHER

    def _is_near_heading(self, node: Tag) -> bool:
        """Checks if the node is near a preceding heading or at a section start.

        An epigraph is valid if it's either close to a preceding heading or if
        it's the first significant content at the start of a container (e.g., body).
        """
        nodes_to_check = 0
        current_sibling = node.find_previous_sibling()
        found_non_ignorable = False

        assert self.config is not None, "Config not bound to strategy"
        while current_sibling and nodes_to_check < self.config.epigraph_heading_proximity_limit:
            assert self.context is not None, "Context not bound to strategy"
            if not is_ignorable_node(current_sibling, self.context.config):
                found_non_ignorable = True
                nodes_to_check += 1
                if isinstance(current_sibling, Tag):
                    status = self._get_sibling_status(current_sibling)
                    if status is SiblingStatus.HEADING:
                        return True
                    if status is SiblingStatus.BLOCKER:
                        # A blocking paragraph before a heading invalidates the epigraph.
                        return False

            current_sibling = current_sibling.find_previous_sibling()

        # If no heading was found, it's a valid epigraph only if there were no
        # preceding non-ignorable siblings found.
        return not found_non_ignorable

    def find_and_apply(
        self,
        start_node: Tag,
        context: BookStyleContext,
        soup: BeautifulSoup,
    ) -> list[Tag] | None:
        """Finds and applies the epigraph strategy (Priority 1).

        This method attempts to identify an epigraph starting at `start_node`. If a
        valid epigraph sequence is found, it is wrapped in a
        `<blockquote class="epigraph">` and the list of processed nodes is returned.

        Mutations:
            - Modifies the DOM in-place by wrapping the identified epigraph nodes
              in a new `<blockquote>` element.

        Rules & Limits:
            - This is the highest priority strategy (Priority 1).
            - Full depth traversal: Yes.
        """
        sequence = self._collect_sequence(start_node)
        # The TTR filter is bypassed for single-paragraph epigraphs by the logic
        # in `_is_candidate_valid`, but the anchor density check is still valuable.
        if sequence and self._is_candidate_valid(sequence):
            self._wrap_nodes_in_blockquote(sequence, soup, bq_class="epigraph")
            assert self.processor, PROCESSOR_UNBOUND_MSG
            self.processor.epigraphs_identified_count += 1
            return sequence
        return None

    def _collect_sequence(self, start_node: Tag) -> list[Tag] | None:
        """Collects a sequence of nodes that match the epigraph criteria.

        An epigraph is a short, high-asymmetry introductory quotation, often
        found at the beginning of a chapter. This method validates a single
        paragraph against a set of strict rules.

        Mutations:
            None.

        Rules & Limits:
            - Node Type: Must be a `<p>` tag.
            - Containment: Must not be inside an existing `<blockquote>`.
            - Proximity: Must be near a preceding heading or be the first
              significant element in its container.
            - Length: The total character length must be 300 characters or less.
            - Typography: The block must have a `text-align: right` style signature.
            - Node Type Safety: Expects `start_node` to be a `Tag`.
        """
        # Rule: Must be a <p> tag and not already in a blockquote.
        if start_node.name != "p" or start_node.find_parent("blockquote"):
            return None

        # Rule: Must be stylistically distinct, within length, and at a valid position.
        if (
            self._has_right_align_style(start_node)
            and self._is_within_max_length(start_node)
            and self._is_near_heading(start_node)
        ):
            return [start_node]

        return None
