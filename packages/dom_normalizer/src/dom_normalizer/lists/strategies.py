"""A collection of specialized list normalization strategies."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString, PageElement

from ..core import MIN_VIABLE_LIST_ITEMS
from ..core.dom_utils import (
    BLOCK_LEVEL_TAGS,
    coerce_class_list,
    find_all_snapshot,
    is_ignorable_node,
    snapshot_iterator,
)
from ..core.list_utils import strip_prefix_from_tag

if TYPE_CHECKING:
    from ..core import BookStyleContext
    from .processor import ListNormalizer


PROCESSOR_UNBOUND_MSG: Final = "Strategy has not been bound to a processor instance."


@dataclass
class ListPrefixInfo:
    """Holds structured information about a detected list prefix."""

    type: str  # 'ul' or 'ol'
    prefix_type: str  # e.g., 'bullet', 'numeric'
    prefix: str  # The full prefix string
    level: int = 0  # Nesting level


UNORDERED_PREFIX_RX: Final = re.compile(r"^\s*([-\*\u2022\u25b6\u2013])\s+")
ORDERED_PREFIX_RX: Final = re.compile(
    r"^\s*(?:(\(?\d+[\.\)])|(\(?[a-zA-Z][\.\)])|(\(?[ivxIVX]+[\.\)]))\s*",
)
LIST_CLASS_KEYWORDS: Final = frozenset(
    {"list", "item", "bullet", "calibre", "idgenparagraphstyle"},
)
_COMPLEX_STRUCTURE_TAGS: Final = frozenset(
    {"ul", "ol", "table", "figure"},
)


class BaseListStrategy(ABC):
    """Abstract base class for all list normalization strategies."""

    def __init__(self) -> None:
        """Initializes the strategy."""
        self.processor: ListNormalizer | None = None
        self.context: BookStyleContext | None = None

    @abstractmethod
    def process(self, soup: BeautifulSoup) -> bool:
        """Executes the strategy on the soup.

        Returns:
            True if any changes were made, False otherwise.
        """
        raise NotImplementedError


class ReconstructionStrategy(BaseListStrategy):
    """Reconstructs semantic lists from sequences of plain paragraphs."""

    def process(self, soup: BeautifulSoup) -> bool:
        """Scans for and processes potential list blocks from paragraphs."""
        assert self.context, PROCESSOR_UNBOUND_MSG
        processed_nodes: set[Tag] = set()
        made_changes = False

        for p_tag in find_all_snapshot(soup, "p"):
            if not isinstance(p_tag, Tag):
                continue
            if p_tag in processed_nodes or self.context.is_inside_code_block(p_tag):
                continue

            if self._is_list_item(p_tag):
                candidates = self._gather_candidates(p_tag)
                if self._validate_list_viability(candidates):
                    self._process_list_block(soup, candidates)
                    processed_nodes.update(candidates)
                    made_changes = True
        return made_changes

    def _is_list_item_by_class(self, tag: Tag) -> bool:
        """Detects a list item based on vendor-specific class names."""
        if not (class_attr := tag.get("class")):
            return False

        for cls in coerce_class_list(class_attr):
            # Per spec, normalize by lowercasing and removing separators to
            # check if any keyword is contained as a substring.
            normalized_cls = cls.lower().replace("_", "").replace("-", "")
            if any(keyword in normalized_cls for keyword in LIST_CLASS_KEYWORDS):
                return True
        return False

    def _is_list_item(self, tag: Tag) -> bool:
        """Determines if a tag is a list item by any heuristic."""
        if tag.name != "p":
            return False

        if self._is_list_item_by_class(tag):
            return True

        text = tag.get_text(strip=True)
        return bool(UNORDERED_PREFIX_RX.match(text) or ORDERED_PREFIX_RX.match(text))

    def _gather_candidates(self, start_tag: Tag) -> list[Tag]:
        """Gathers a sequence of potential list-related paragraphs."""
        candidates = [start_tag]
        current_node: PageElement | None = start_tag
        last_tag_was_list_item = self._is_list_item(start_tag)

        while current_node := current_node.next_sibling:
            if is_ignorable_node(current_node):
                continue

            if not (
                isinstance(current_node, Tag) and current_node.name == "p"
            ):  # pyright: ignore[reportUnnecessaryIsInstance]
                break

            if self._is_list_item(current_node):
                candidates.append(current_node)
                last_tag_was_list_item = True
            elif last_tag_was_list_item:
                candidates.append(current_node)
                last_tag_was_list_item = False
            else:
                break
        return candidates

    def _validate_list_viability(self, candidates: list[Tag]) -> bool:
        """Applies the "Rollback Guard" to prevent creating single-item lists."""
        list_item_count = sum(bool(self._is_list_item(tag)) for tag in candidates)
        return list_item_count >= MIN_VIABLE_LIST_ITEMS

    def _get_prefix_info(self, tag: Tag) -> ListPrefixInfo | None:
        """Analyzes a tag to extract list prefix information from text or class."""
        text = tag.get_text(strip=True)

        # Priority 1: Check for textual prefixes (e.g., "1.", "*").
        if unordered_match := UNORDERED_PREFIX_RX.match(text):
            return ListPrefixInfo(
                type="ul",
                prefix_type="bullet",
                prefix=unordered_match.group(0),
                level=1,  # Assume bullets are level 1
            )
        if ordered_match := ORDERED_PREFIX_RX.match(text):
            prefix_type = "unknown"
            level = 0
            if ordered_match.group(1):
                prefix_type = "numeric"
                level = 1
            elif ordered_match.group(2):
                prefix_type = "alpha"
                level = 2
            elif ordered_match.group(3):
                prefix_type = "roman"
                level = 3
            return ListPrefixInfo(
                type="ol",
                prefix_type=prefix_type,
                prefix=ordered_match.group(0),
                level=level,
            )

        # Priority 2: If no textual prefix, check for a class-based list item.
        if self._is_list_item_by_class(tag):
            return ListPrefixInfo(
                type="ul",  # Default to unordered for class-based lists
                prefix_type="class_based",
                prefix="",  # No textual prefix to strip
                level=1,
            )
        return None

    def _handle_new_list_item(
        self,
        prefix_info: ListPrefixInfo,
        tag: Tag,
        soup: BeautifulSoup,
        list_block_div: Tag,
        container_stack: list[Tag],
        level_stack: list[int],
        current_li: Tag | None,
    ) -> Tag:
        """Manages the list container stack and appends a new list item."""
        assert self.processor, PROCESSOR_UNBOUND_MSG
        # Pop from the stack until the current level is correct
        while level_stack and prefix_info.level < level_stack[-1]:
            level_stack.pop()
            container_stack.pop()

        if not container_stack:
            # This is a new top-level list
            new_container = soup.new_tag(prefix_info.type)
            list_block_div.append(new_container)
            self._track_list_creation(prefix_info.type)
            container_stack.append(new_container)
            level_stack.append(prefix_info.level)
        elif prefix_info.level > level_stack[-1]:
            # This is a new nested list
            if not current_li:
                # This should not be reachable if candidate gathering is correct,
                # but as a safeguard, we return the last known li.
                return current_li  # type: ignore
            new_container = soup.new_tag(prefix_info.type)
            current_li.append(new_container)
            self._track_list_creation(prefix_info.type)
            container_stack.append(new_container)
            level_stack.append(prefix_info.level)

        current_container = container_stack[-1]
        return self._append_list_item(
            soup,
            tag,
            current_container,
            prefix_info,
        )

    def _process_list_block(self, soup: BeautifulSoup, candidates: list[Tag]) -> None:
        """Reconstructs a validated block of paragraphs into a semantic list."""
        assert self.context, PROCESSOR_UNBOUND_MSG
        list_block_div = soup.new_tag("div", attrs={"class": "list-block"})
        candidates[0].insert_before(list_block_div)

        container_stack: list[Tag] = []
        level_stack: list[int] = []
        current_li: Tag | None = None

        for tag in candidates:
            if self.context.is_inside_code_block(tag):
                continue

            if prefix_info := self._get_prefix_info(tag):
                current_li = self._handle_new_list_item(
                    prefix_info,
                    tag,
                    soup,
                    list_block_div,
                    container_stack,
                    level_stack,
                    current_li,
                )
            elif current_li:
                # This is a continuation paragraph
                self._append_continuation(tag, current_li)

    def _track_list_creation(self, list_type: str) -> None:
        """Increments telemetry counters for list reconstruction."""
        assert self.processor, PROCESSOR_UNBOUND_MSG
        if list_type == "ul":
            self.processor.unordered_lists_recovered += 1
        elif list_type == "ol":
            self.processor.ordered_lists_recovered += 1

    def _append_list_item(
        self,
        soup: BeautifulSoup,
        tag: Tag,
        container: Tag,
        prefix_info: ListPrefixInfo,
    ) -> Tag:
        """Creates a new `<li>` element and appends it to the current list."""
        assert self.processor, PROCESSOR_UNBOUND_MSG
        li = soup.new_tag("li")
        p = soup.new_tag("p")

        strip_prefix_from_tag(tag, prefix_info.prefix)
        # The contents of the original tag are moved into the new <p>
        p.extend(tag.contents)
        li.append(p)

        # The original tag is now empty and can be removed.
        tag.extract()

        self.processor.total_raw_paragraphs_purged += 1
        container.append(li)

        return li

    def _append_continuation(
        self,
        tag: Tag,
        current_li: Tag,
    ) -> Tag:
        """Appends a continuation paragraph to an existing list item."""
        assert self.processor, PROCESSOR_UNBOUND_MSG
        # The spec requires appending the paragraph, not merging text.
        current_li.append(tag)
        self.processor.multiline_items_welded += 1
        self.processor.total_raw_paragraphs_purged += 1
        return current_li


class SanitizationStrategy(BaseListStrategy):
    """Sanitizes existing lists by fixing invalid child structures."""

    def process(self, soup: BeautifulSoup) -> bool:
        """Finds and sanitizes all existing `<ul>` and `<ol>` tags."""
        assert self.context, PROCESSOR_UNBOUND_MSG
        assert self.processor, PROCESSOR_UNBOUND_MSG
        made_changes = False
        for list_tag in find_all_snapshot(soup, ("ul", "ol")):
            if not isinstance(list_tag, Tag):
                continue
            if self.context.is_inside_code_block(list_tag):
                continue

            repaired_this_list = False
            if self._has_orphan_children(list_tag):
                self._wrap_orphan_children(list_tag, soup)
                repaired_this_list = True
                made_changes = True

            if self._ensure_list_block_wrapper(soup, list_tag):
                repaired_this_list = True
                made_changes = True

            if repaired_this_list:
                self.processor.lists_sanitized += 1

        return made_changes

    def _is_complex_or_block_orphan(self, child: PageElement) -> bool:
        """Checks if an orphan is a block-level tag or contains complex structures."""
        if not isinstance(child, Tag):
            return False

        # Check if the tag itself is a known block-level tag
        if child.name in BLOCK_LEVEL_TAGS:
            return True

        # Check if the tag contains nested complex structures
        return bool(child.find(_COMPLEX_STRUCTURE_TAGS))

    def _has_orphan_children(self, list_tag: Tag) -> bool:
        """Checks if a list tag contains any direct children other than `<li>`."""
        for child in list_tag.children:
            if isinstance(child, NavigableString) and not child.strip():
                continue
            if not (isinstance(child, Tag) and child.name == "li"):
                return True
        return False

    def _wrap_orphan_children(self, list_tag: Tag, soup: BeautifulSoup) -> None:
        """Wraps any direct non-<li> children of a list tag in <li> tags."""
        for child in snapshot_iterator(list_tag.children):
            if (isinstance(child, NavigableString) and not child.strip()) or (
                isinstance(child, Tag) and child.name == "li"
            ):
                continue

            li = soup.new_tag("li")
            child.replace_with(li)
            if self._is_complex_or_block_orphan(child):
                li.append(child)
            else:
                p = soup.new_tag("p")
                p.append(child)
                li.append(p)

    def _ensure_list_block_wrapper(self, soup: BeautifulSoup, list_tag: Tag) -> bool:
        """Ensures a list tag is wrapped in a `<div class="list-block">`."""
        parent = list_tag.parent
        # Do not wrap nested lists, which are correctly parented by an <li>
        if parent and parent.name == "li":
            return False

        if (
            parent
            and parent.name == "div"
            and "list-block" in coerce_class_list(parent.get("class"))
        ):
            return False

        wrapper = soup.new_tag("div", attrs={"class": "list-block"})
        list_tag.wrap(wrapper)
        return True


class FusionStrategy(BaseListStrategy):
    """Fuses adjacent, fragmented lists of the same type."""

    def process(self, soup: BeautifulSoup) -> bool:
        """Finds and fuses fragmented, logically contiguous lists."""
        assert self.context, PROCESSOR_UNBOUND_MSG
        made_changes = False
        processed_lists = set()

        for list_tag in find_all_snapshot(soup, ["ul", "ol"]):
            if not isinstance(list_tag, Tag):
                continue
            if id(list_tag) in processed_lists or self.context.is_inside_code_block(
                list_tag,
            ):
                continue
            if fused_list_id := self._try_fuse_with_next(list_tag):
                processed_lists.add(fused_list_id)
                made_changes = True

        return made_changes

    def _get_list_from_simple_wrapper(
        self,
        wrapper_node: PageElement,
        list_type: str,
    ) -> Tag | None:
        """If a node is a simple div wrapping a list, returns the inner list."""
        if not (isinstance(wrapper_node, Tag) and wrapper_node.name == "div"):
            return None
        meaningful_children = [
            child for child in wrapper_node.contents if not is_ignorable_node(child)
        ]
        if len(meaningful_children) == 1 and isinstance(meaningful_children[0], Tag):
            inner_node = meaningful_children[0]
            if inner_node.name == list_type:
                return inner_node
        return None

    def _try_fuse_with_next(self, list_a: Tag) -> int | None:
        """Attempts to fuse a given list with the next adjacent list."""
        noise_to_remove: list[PageElement] = []
        next_node: PageElement | None = list_a.next_sibling

        while next_node:
            if is_ignorable_node(next_node):
                noise_to_remove.append(next_node)
                next_node = next_node.next_sibling
                continue

            list_b: Tag | None = None
            wrapper_to_remove: PageElement | None = None

            if isinstance(next_node, Tag) and next_node.name == list_a.name:
                list_b = next_node
            elif list_from_wrapper := self._get_list_from_simple_wrapper(
                next_node,
                list_a.name,
            ):
                list_b = list_from_wrapper
                wrapper_to_remove = next_node

            if list_b:
                list_b_id = id(list_b)
                self._perform_list_fusion(list_a, list_b, noise_to_remove)
                if wrapper_to_remove:
                    wrapper_to_remove.extract()
                return list_b_id

            break
        return None

    def _perform_list_fusion(
        self,
        list_a: Tag,
        list_b: Tag,
        noise_to_remove: list[PageElement],
    ) -> None:
        """Executes the fusion of two lists and cleans up intermediate nodes."""
        assert self.processor, PROCESSOR_UNBOUND_MSG
        list_a.extend(list_b.find_all("li", recursive=False))

        for noise in noise_to_remove:
            noise.extract()
        list_b.decompose()  # pyright: ignore[reportAttributeAccessIssue] # Tag.decompose is present at runtime

        self.processor.lists_fused += 1
