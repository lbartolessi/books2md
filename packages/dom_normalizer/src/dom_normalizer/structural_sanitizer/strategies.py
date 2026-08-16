"""A collection of specialized sanitization strategies for the StructuralSanitizer.

This module implements the Strategy pattern for the StructuralSanitizer. Each
strategy is responsible for a single, specific step of the sanitization process,
such as promoting inline styles, purging attributes, collapsing <br> tags, or
running final cleanup passes. This separation of concerns makes the system more
modular, testable, and extensible.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from itertools import groupby
from typing import TYPE_CHECKING, Final

from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString

from ..core.dom_utils import (
    coerce_class_list,
    find_all_snapshot,
    normalize_style_attribute,
    normalize_whitespace,
    snapshot_iterator,
    strip_css_properties,
)

if TYPE_CHECKING:
    from ..core import BookStyleContext
    from .processor import StructuralSanitizer

log = logging.getLogger(__name__)

# --- Module-level Constants ---

#: Message for assertion errors when a strategy is used without being bound to a processor.
PROCESSOR_UNBOUND_MSG: Final[str] = (
    "Strategy has not been bound to a processor instance."
)

#: Legacy presentational attributes to be purged and persisted for forensics.
_LEGACY_ATTRS_TO_PURGE = frozenset(["align", "bgcolor"])

#: Layout-related CSS properties to be purged from general elements in Step 3.
_GENERAL_LAYOUT_PROPS_TO_PURGE = frozenset(
    ["margin-left", "padding-left", "float", "position", "background-color"],
)

#: Layout-related CSS properties to be purged from `blockquote-element` nodes
#: in the epilogue. This includes all indentation properties.
_BLOCKQUOTE_LAYOUT_PROPS_TO_PURGE = frozenset(
    [
        "margin",
        "margin-top",
        "margin-right",
        "margin-bottom",
        "margin-left",
        "padding",
        "padding-top",
        "padding-right",
        "padding-bottom",
        "padding-left",
        "float",
        "position",
    ],
)

#: Tags that are considered renderable content even if they contain no text.
_MEDIA_TAGS = frozenset(
    ["img", "svg", "video", "audio", "picture", "source", "canvas", "iframe", "math"],
)

#: Tags that are eligible for removal if they are deemed structurally empty.
_PURGEABLE_EMPTY_TAGS = frozenset(
    [
        "p",
        "div",
        "span",
        "em",
        "strong",
        "i",
        "b",
        "u",
        "font",
        "a",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "blockquote",
        "pre",
        "li",
        "td",
        "th",
    ],
)

#: Minimum number of classes a node must have to trigger sorting.
_MIN_CLASSES_FOR_SORTING = 2


class BaseStrategy:
    """Base class for all sanitizer strategies, providing context."""

    def __init__(self, context: BookStyleContext):
        """Initializes the strategy with context."""
        self.context = context
        self.processor: StructuralSanitizer | None = None


class NodeStrategy(BaseStrategy, ABC):
    """Abstract base class for strategies that process a single DOM node."""

    @abstractmethod
    def process(self, node: Tag) -> None:
        """Executes the strategy's logic on a single node."""
        raise NotImplementedError


class DocumentStrategy(BaseStrategy, ABC):
    """Abstract base class for strategies that process the entire document."""

    @abstractmethod
    def process(self, soup: BeautifulSoup) -> None:
        """Executes the strategy's logic on the entire document."""
        raise NotImplementedError


class InlineStylePromotionStrategy(NodeStrategy):
    """Strategy for Steps 1 & 2: Promoting inline styles to semantic classes."""

    def process(self, node: Tag) -> None:
        """Promotes inline float and indent styles to classes.

        Args:
            node: The block-level node to process.
        """
        self._step1_inline_float_fingerprinting(node)
        self._step2_structural_indentation_promotion(node)

    def _step1_inline_float_fingerprinting(self, node: Tag) -> None:
        """Step 1: Promotes inline `float` styles to a semantic class."""
        if self.context.normalize_inline_floats(node):
            assert self.processor, PROCESSOR_UNBOUND_MSG
            self.processor.increment_inline_floats_normalized()

    def _step2_structural_indentation_promotion(self, node: Tag) -> None:
        """Step 2: Promotes indentation styles to a class and adds a tracker."""
        if self.context.normalize_inline_indents(node):
            assert self.processor, PROCESSOR_UNBOUND_MSG
            self.processor.increment_inline_indents_normalized()


class AttributePurgeStrategy(NodeStrategy):
    """Strategy for Step 3: Purging legacy attributes and layout styles."""

    def process(self, node: Tag) -> None:
        """Orchestrates the purging of legacy and inline layout styles.

        Args:
            node: The block-level node to process.
        """
        if self._purge_legacy_attributes(node):
            assert self.processor, PROCESSOR_UNBOUND_MSG
            self.processor.increment_layout_attributes_persisted()

        self._purge_layout_styles(node)
        self._enforce_class_order(node)

    def _purge_legacy_attributes(self, node: Tag) -> bool:
        """Scrubs legacy presentational attributes."""
        purged = False
        for attr in _LEGACY_ATTRS_TO_PURGE:
            if node.has_attr(attr):
                value = node[attr]
                del node[attr]
                node[f"data-orig-{attr}"] = value
                purged = True
        return purged

    def _purge_layout_styles(self, node: Tag) -> bool:
        """Removes captured layout properties from the style attribute."""
        if node.has_attr("data-bq-promoted"):
            return False
        if not node.has_attr("style"):
            return False

        original_style = normalize_style_attribute(node.get("style"))
        if not original_style:
            return False

        cleaned_style = strip_css_properties(
            original_style,
            _GENERAL_LAYOUT_PROPS_TO_PURGE,
        )
        if cleaned_style == original_style:
            return False

        if cleaned_style:
            node["style"] = cleaned_style
        elif "style" in node.attrs:
            del node["style"]
        return True

    def _enforce_class_order(self, node: Tag) -> None:
        """Sorts a node's class list according to deterministic rules."""
        if not isinstance(node, Tag) or not node.has_attr("class"):
            return

        classes = coerce_class_list(node.get("class"))
        if len(classes) < _MIN_CLASSES_FOR_SORTING:
            return

        def sort_key(c: str) -> tuple[int, str]:
            if c == "blockquote-element":
                return (0, c)
            return (1, c) if c == "floating-element" else (2, c)

        classes.sort(key=sort_key)
        node["class"] = " ".join(classes)


class BrCollapseStrategy(NodeStrategy):
    """Strategy for Step 4: Intelligently collapsing <br> tags."""

    def __init__(self, context: BookStyleContext):
        super().__init__(context)
        self.poetic_classes_substrings = frozenset(
            context.config.poetic_classes_substrings,
        )
        self.min_br_for_poetic_metrics = context.config.min_br_for_poetic_metrics
        self.max_avg_words_per_line_poetic = (
            context.config.max_avg_words_per_line_poetic
        )

    def process(self, node: Tag) -> None:
        """Intelligently collapses `<br>` tags based on context.

        Args:
            node: The block-level node to process.
        """
        br_tags = find_all_snapshot(node, "br")
        if not br_tags:
            return

        if self._is_poetic_context(node):
            assert self.processor, PROCESSOR_UNBOUND_MSG
            self.processor.increment_poetic_br_tags_preserved(len(br_tags))
            return

        assert self.processor, PROCESSOR_UNBOUND_MSG
        for br in br_tags:
            br.replace_with(NavigableString(" "))
            self.processor.increment_br_tags_collapsed()

    def _is_poetic_context(self, node: Tag) -> bool:
        """Determines if a node is in a poetic context."""
        return self._has_poetic_semantic_class(
            node,
        ) or self._is_poetic_by_metrics(node)

    def _has_poetic_semantic_class(self, node: Tag) -> bool:
        """Checks if a node or any of its ancestors has a poetic class."""
        if not isinstance(node, Tag):
            return False

        nodes_to_check = [node, *list(node.parents)]
        for current_node in nodes_to_check:
            if isinstance(current_node, Tag) and current_node.has_attr("class"):
                classes = coerce_class_list(current_node.get("class"))
                for c in classes:
                    c_lower = c.lower()
                    if any(
                        keyword in c_lower for keyword in self.poetic_classes_substrings
                    ):
                        return True
        return False

    def _extract_text_lines_around_brs(self, node: Tag) -> list[str]:
        """Splits a node's content into text lines based on `<br>` tags."""
        lines = []
        current_line_parts = []
        for descendant in node.descendants:
            if isinstance(descendant, Tag) and descendant.name == "br":
                lines.append(" ".join("".join(current_line_parts).split()))
                current_line_parts = []
            elif isinstance(descendant, NavigableString):
                current_line_parts.append(str(descendant))

        lines.append(" ".join("".join(current_line_parts).split()))
        return [line for line in lines if line]

    def _is_poetic_by_metrics(self, node: Tag) -> bool:
        """Checks if a node's content is poetic based on textual metrics."""
        if not isinstance(node, Tag):
            return False

        br_tags = node.find_all("br")
        if len(br_tags) < self.min_br_for_poetic_metrics:
            return False

        lines = self._extract_text_lines_around_brs(node)
        if not lines:
            return False

        total_words = sum(len(line.split()) for line in lines)
        return (total_words / len(lines)) <= self.max_avg_words_per_line_poetic


class EpilogueStrategy(DocumentStrategy):
    """Strategy for Step 5: Final cleanup passes on the entire document."""

    def process(self, soup: BeautifulSoup) -> None:
        """Executes the final four cleanup sub-passes.

        Args:
            soup: The entire DOM after the main processing loop.
        """
        self._epilogue_strip_blockquote_indent_styles(soup)
        self._epilogue_remove_tracking_attrs(soup)
        self._epilogue_purge_empty_nodes(soup)
        self._epilogue_coalesce_text_nodes(soup)

    def _epilogue_remove_tracking_attrs(self, soup: BeautifulSoup) -> None:
        """Epilogue Pass 1: Purges all temporary tracking attributes."""
        for tag in soup.select("[data-bq-promoted], [data-dn-indent-level]"):
            if tag.has_attr("data-bq-promoted"):
                del tag["data-bq-promoted"]
            if tag.has_attr("data-dn-indent-level"):
                del tag["data-dn-indent-level"]

    def _epilogue_strip_blockquote_indent_styles(self, soup: BeautifulSoup) -> None:
        """Epilogue Pass 2: Strips layout styles from promoted blockquotes."""
        # The `data-bq-promoted` attribute is the canonical tracker for nodes
        # that had their indentation styles promoted.
        for node in soup.select("[data-bq-promoted='1']"):
            if not node.has_attr("style"):
                continue
            if original_style := normalize_style_attribute(node.get("style")):
                if cleaned_style := strip_css_properties(
                    original_style,
                    _BLOCKQUOTE_LAYOUT_PROPS_TO_PURGE,
                ):
                    node["style"] = cleaned_style
                elif "style" in node.attrs:
                    del node["style"]

    def _epilogue_purge_empty_nodes(self, soup: BeautifulSoup) -> None:
        """Epilogue Pass 3: Removes dead, structurally empty elements."""
        nodes_to_check = find_all_snapshot(soup, _PURGEABLE_EMPTY_TAGS)
        for node in reversed(nodes_to_check):
            if (
                node.parent is not None
                and isinstance(node, Tag)
                and not self._has_renderable_content(node)
            ):
                node.decompose()
                assert self.processor, PROCESSOR_UNBOUND_MSG
                self.processor.increment_empty_nodes_purged()

    def _coalesce_string_group(self, string_nodes: list[NavigableString]) -> None:
        """Merges a contiguous sequence of NavigableString nodes into one."""
        if not string_nodes:
            return

        anchor_node = string_nodes[0]
        if anchor_node.parent is None:
            return

        full_text = normalize_whitespace("".join(str(s) for s in string_nodes))
        anchor_node.replace_with(NavigableString(full_text))
        for node_to_remove in string_nodes[1:]:
            node_to_remove.decompose()

    def _coalesce_adjacent_text_nodes_in_parent(self, parent_node: Tag) -> None:
        """Merges adjacent NavigableString children within a given parent tag."""
        children_tuple = snapshot_iterator(parent_node.children)
        for is_string, group in groupby(
            children_tuple,
            lambda c: isinstance(c, NavigableString),
        ):
            if is_string:
                string_nodes = [
                    s for s in group if isinstance(s, NavigableString) and s.parent
                ]
                if len(string_nodes) > 1:
                    self._coalesce_string_group(string_nodes)

    def _epilogue_coalesce_text_nodes(self, soup: BeautifulSoup) -> None:
        """Epilogue Pass 4: Performs a tree-wide merge of adjacent text nodes."""
        # Find all tags that can contain text, avoiding duplicates.
        # We build a static set of parents first to avoid issues with iterating
        # over a list of nodes while modifying the tree.
        parents_to_process = {
            text_node.parent
            for text_node in soup.find_all(string=True)
            if text_node.parent and text_node.parent.name != "[document]"
        }

        for parent in parents_to_process:
            self._coalesce_adjacent_text_nodes_in_parent(parent)

    def _has_renderable_content(self, node: Tag) -> bool:
        """Checks if a node contains any non-whitespace text or media elements."""
        return (
            True
            if node.get_text(strip=True)
            else bool(
                node.find(list(_MEDIA_TAGS)),
            )
        )
