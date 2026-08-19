"""Abstract base class for all blockquote detection strategies."""

from __future__ import annotations

import itertools
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Final

from bs4 import BeautifulSoup, Tag
from bs4.element import PageElement

from ..core import BookStyleContext, EngineConfiguration
from ..core.dom_utils import coerce_class_list, get_tag_identifier, is_ignorable_node

if TYPE_CHECKING:
    from .processor import BlockquoteProcessor


log = logging.getLogger(__name__)

PROCESSOR_UNBOUND_MSG: Final[str] = (
    "Strategy has not been bound to a processor instance."
)


class BaseBlockquoteStrategy(ABC):
    """Abstract base class for all blockquote detection strategies."""

    def __init__(self) -> None:
        self.config: EngineConfiguration | None = None
        self.context: BookStyleContext | None = None
        """Initializes the strategy.

        Mutations:
            - Sets `self.processor` to None initially. It will be bound
              when injected into a BlockquoteProcessor.

        Rules & Limits:
            - Instance Lifecycle: Assumes this instance is scoped to a single book,
              per Global Directive #3.
        """
        self.processor: BlockquoteProcessor | None = None

    @abstractmethod
    def find_and_apply(
        self,
        start_node: Tag,
        context: BookStyleContext,
        soup: BeautifulSoup,
    ) -> list[Tag] | None:
        """Finds and processes a sequence of nodes according to the strategy.

        This method orchestrates the core logic of a strategy: it attempts to
        collect a sequence of candidate nodes starting from `start_node`. If a
        sequence is found, it is validated using the TTR filter. If valid, the
        nodes are wrapped in a `<blockquote>` tag, and the list of processed
        nodes is returned.

        Mutations:
            - May perform in-place modifications on the `soup` object by calling
              `_wrap_nodes_in_blockquote` if a valid sequence is found.

        Rules & Limits:
            - Full depth traversal: Yes. The collection logic within each strategy
              should traverse siblings as needed.
        """
        raise NotImplementedError

    def _get_content_stats(self, nodes: list[Tag]) -> dict[str, int]:
        """Calculates content metrics for a list of nodes.

        This helper iterates through a list of nodes once to compute various
        metrics required for validation, such as word count, tag count, and
        character counts for text and anchors.

        Args:
            nodes: A list of candidate `Tag` objects.

        Returns:
            A dictionary containing the calculated metrics:
            - "total_words": Total number of words.
            - "total_tags": Total number of tags (including main nodes and their
              direct children).
            - "anchor_chars": Total number of characters within `<a>` tags.
            - "total_chars": Total number of characters in the nodes.
        """
        total_words = 0
        # Count container paragraphs + direct child tags to avoid over-penalizing deep inline markup.
        inner_tags = sum(
            len(p.find_all(True, recursive=False)) for p in nodes
        )
        total_tags = len(nodes) + inner_tags
        anchor_chars = 0
        total_chars = 0

        for node in nodes:
            text = node.get_text(strip=True)
            total_words += len(text.split())
            total_chars += len(text)
            for anchor in node.find_all("a"):
                anchor_chars += len(anchor.get_text(strip=True))

        return {
            "total_words": total_words,
            "total_tags": total_tags,
            "anchor_chars": anchor_chars,
            "total_chars": total_chars,
        }

    def _is_candidate_valid(self, nodes: list[Tag]) -> bool:
        """Applies validation filters to a candidate blockquote sequence.

        This filter prevents the processor from misinterpreting structured,
        non-prose content (like a table of contents or navigation menu) as a
        blockquote by checking the Text-to-Tag Ratio (TTR) and anchor density.

        Args:
            nodes (list[Tag]): A list of candidate `Tag` objects forming a potential
                blockquote.

        Returns:
            True if the candidate passes all validation filters, False otherwise.

        Rules & Limits:
            - TTR Calculation: TTR = (Total Words) / (Total Tag Nodes +
              TTR_SMOOTHING_FACTOR).
            - TTR Threshold: The candidate is invalid if TTR is less than 3.0
              (for multi-node sequences).
            - Anchor Tag Threshold: The candidate is invalid if anchor tags (`<a>`)
              constitute more than 30% of the total character tokens within the
              sequence.
            - Node Type Safety: Assumes `nodes` contains only `Tag` objects.
              Behavior is undefined for `NavigableString`.
        """
        if not nodes:
            return False

        stats = self._get_content_stats(nodes)

        # The anchor density check is first as it's a strong signal for
        # non-quote content and also handles the zero-character case.
        if not self._is_anchor_density_valid(
            stats["anchor_chars"],
            stats["total_chars"],
        ):
            return False

        return bool(
            self._is_ttr_valid(nodes, stats["total_words"], stats["total_tags"]),
        )

    def _is_ttr_valid(
        self,
        nodes: list[Tag],
        total_words: int,
        total_tags: int,
    ) -> bool:
        """Validates the Text-to-Tag Ratio (TTR) for a candidate sequence.

        This filter is applied only to sequences with more than one node to avoid
        penalizing valid single-paragraph quotes.

        Args:
            nodes: The list of candidate nodes.
            total_words: The total word count in the nodes.
            total_tags: The total tag count in the nodes.

        Returns:
            True if the TTR is valid or if the check is skipped, False otherwise.
        """
        if len(nodes) <= 1:
            return True

        assert self.config is not None, "Config not bound to strategy"
        ttr = total_words / (total_tags + self.config.blockquote_ttr_smoothing_factor)
        if ttr < self.config.blockquote_ttr_threshold:
            log.debug(
                "Candidate rejected by TTR filter (TTR < %.1f). TTR: %.2f",
                self.config.blockquote_ttr_threshold,
                ttr,
            )
            return False
        return True

    def _is_anchor_density_valid(self, anchor_chars: int, total_chars: int) -> bool:
        """Validates the anchor text density for a candidate sequence.

        This filter prevents navigation menus or lists of links from being
        misidentified as blockquotes. It also rejects candidates with no text
        content.

        Args:
            anchor_chars: The total character count within anchor tags.
            total_chars: The total character count in the nodes.

        Returns:
            True if the anchor density is within the threshold, False otherwise.
        """
        if total_chars == 0:
            return False

        assert self.config is not None, "Config not bound to strategy"
        anchor_ratio = anchor_chars / total_chars
        if anchor_ratio > self.config.blockquote_anchor_density_threshold:
            log.debug(
                "Candidate rejected by anchor density filter (>%.0f%%). Ratio: %.2f",
                self.config.blockquote_anchor_density_threshold * 100,
                anchor_ratio,
            )
            return False
        return True

    def _wrap_nodes_in_blockquote(
        self,
        nodes: list[Tag],
        soup: BeautifulSoup,
        bq_class: str | list[str] | None = None,
    ) -> Tag | None:
        """Wraps a list of consecutive sibling DOM nodes in a single `<blockquote>`.

        This helper creates a new `blockquote` tag, inserts it into the DOM
        before the first node in the provided list, and then moves all the
        nodes from the list inside the new blockquote.

        Args:
            nodes: A list of consecutive sibling DOM nodes to wrap. All nodes must
                share the same parent and be in document order.
            soup: The BeautifulSoup object, used as a factory.
            bq_class: An optional CSS class or list of classes to add to the
                new blockquote.

        Returns:
            The newly created `<blockquote>` tag, or `None` if no nodes were
            provided.

        Raises:
            ValueError: If the nodes do not share a common parent, are not
                consecutive, are not in document order, or if a strategy error
                is detected.

        Mutations:
            - Creates a new `<blockquote>` tag.
            - Moves the `nodes` from their original parent to be children of the new
              `<blockquote>`.
            - Inserts the new `<blockquote>` into the DOM before the original position
              of the first node in the `nodes` list.
            - The original nodes are detached from the main tree during reparenting.

        Rules & Limits:
            - Sibling Invariant: All nodes in the `nodes` list must be consecutive
              siblings sharing a common parent and preserving document order. This
              method enforces this contract.
            - Pandoc Invariant: This method ensures that multiple paragraph nodes
              are nested within a single `<blockquote>`, which is compatible with
              Pandoc's multi-paragraph blockquote parsing.
        """
        if not nodes:
            return None

        first_parent = self._validate_common_parent(nodes)

        try:
            parent_contents: list[PageElement] = list(first_parent.contents)
            # Create a mapping from node to its index for O(1) lookups.
            # This avoids an O(n^2) sort by not calling .index() repeatedly.
            node_to_index = {node: i for i, node in enumerate(parent_contents)}
            # Defensively sort the nodes by their DOM order.
            nodes.sort(key=lambda node: node_to_index[node])
            # Get the indices from the now-sorted list of nodes.
            indices = [node_to_index[node] for node in nodes]
        except (KeyError, AttributeError) as e:
            # Collect debug information about the offending nodes to aid tracing
            # misbehaving strategies without a debugger.
            try:
                offending_nodes = [
                    {
                        "repr": repr(node),
                        "type": type(node).__name__,
                        # Use a short content/repr snippet if available, fall back gracefully.
                        "snippet": (
                            getattr(node, "text", None)
                            or getattr(node, "string", None)
                            or (repr(node)[:200] if repr(node) else None)
                        ),
                    }
                    for node in nodes
                    if node not in getattr(first_parent, "contents", ())
                ]
            except (TypeError, AttributeError, ValueError):
                # If any introspection above fails, fall back to a simpler representation.
                offending_nodes = [repr(node) for node in nodes]

            log.critical(
                "Blockquote wrapping failed due to a contract violation: a strategy passed a "
                "node that was not found in its parent's contents. This is a strategy "
                "implementation error. Exception: %s. Offending nodes: %r",
                e,
                offending_nodes,
            )
            raise ValueError(
                "A node to be wrapped was not found in its parent's contents during sorting.",
            ) from e

        # Document order is guaranteed by the sort above. This validates consecutiveness.
        self._validate_consecutiveness(indices, parent_contents)

        first_node = nodes[0]
        blockquote = soup.new_tag("blockquote")
        if bq_class:
            # Normalize to a list to ensure consistent attribute structure,
            # adhering to the multi-valued attribute rule.
            # Use coerce_class_list for robust handling of various input types
            # and to satisfy type checkers.
            blockquote["class"] = coerce_class_list(bq_class)  # type: ignore[assignment]

        first_node.insert_before(blockquote)

        for node in nodes:
            if not isinstance(node, Tag): # pyright: ignore[reportUnnecessaryIsInstance]
                log.critical(
                    "Blockquote wrapping failed due to a contract violation: a strategy passed a "
                    "non-Tag object to be wrapped. Received type: %s",
                    type(node).__name__,
                )
                raise TypeError(
                    "Blockquote wrapping failed: strategies must only pass Tag objects to be wrapped. "
                    f"Received type: {type(node).__name__}",
                )
            # Per review, add a final guard to ensure the node's parent has not
            # changed since the initial validation. This prevents race conditions
            # or silent failures if a node is detached during processing.
            if node.parent is not first_parent:
                log.critical(
                    "Blockquote wrapping failed due to a contract violation: a strategy passed "
                    "a node whose parent changed during processing. This indicates a state "
                    "inconsistency or a detached node. Expected parent ID: %s, actual: %s. Node: %r",
                    id(first_parent),
                    id(node.parent),
                    repr(node),
                )
                raise ValueError(
                    "A node's parent was unexpectedly changed or detached during blockquote wrapping.",
                )
            blockquote.append(node)

        return blockquote

    def _get_prev_non_ignorable_sibling(self, node: Tag) -> Tag | None:
        """Finds the previous non-ignorable sibling of a node."""
        sibling = node.previous_sibling
        assert self.config is not None, "Config not bound to strategy"
        while sibling and is_ignorable_node(sibling, self.config):
            sibling = sibling.previous_sibling
        return sibling if isinstance(sibling, Tag) else None

    def _get_next_non_ignorable_sibling(self, node: Tag) -> Tag | None:
        """Finds the next non-ignorable sibling of a node."""
        sibling = node.next_sibling
        assert self.config is not None, "Config not bound to strategy"
        while sibling and is_ignorable_node(sibling, self.config):
            sibling = sibling.next_sibling
        return sibling if isinstance(sibling, Tag) else None

    def _validate_common_parent(self, nodes: list[Tag]) -> Tag:
        """Validates that all nodes share a common parent and returns it."""
        first_parent = nodes[0].parent
        if not first_parent:
            log.critical(
                "Blockquote wrapping failed due to a contract violation: a strategy passed a "
                "list of nodes where the first node has no parent. This can happen with "
                "detached or top-level nodes. This is a strategy implementation error.",
            )
            raise ValueError("Nodes to be wrapped must have a parent.")

        if any(node.parent is not first_parent for node in nodes[1:]):
            log.critical(
                "Blockquote wrapping failed due to a contract violation: a strategy passed a "
                "list of nodes that do not share a common parent. This is a strategy "
                "implementation error.",
            )
            raise ValueError(
                "All nodes to be wrapped in a blockquote must share the same parent.",
            )
        return first_parent

    def _format_node_for_log(self, node: Any) -> str:
        """Return a compact, log-friendly representation of a node.

        The goal is to aid debugging without bloating log entries.
        """
        try:
            tag = getattr(node, "name", None) or type(node).__name__
        except AttributeError:  
            tag = type(node).__name__
        if not tag:
            tag = "UnknownType"

        text = ""
        try:
            # Common attributes where textual content may be stored.
            text_attr = (
                getattr(node, "text", None)
                or getattr(node, "string", None)
                or getattr(node, "data", None)
            )
            if isinstance(text_attr, str):
                text = text_attr.strip()
        except AttributeError:  
            # If introspection fails, fall back to an empty string.
            text = ""

        if text and self.config:
            assert self.config is not None
            return get_tag_identifier(node, self.config.tag_identifier_attr_value_limit)
        return f"<{tag}>"

    def _validate_consecutiveness(
        self,
        indices: list[int],
        parent_contents: list[PageElement],
    ) -> None:
        """Validates that node indices are consecutive or separated only by ignorable nodes.

        This check enforces the contract that strategies must pass a list of
        sibling nodes that are either physically adjacent or separated only by
        ignorable content (like whitespace or comments). Document order is
        guaranteed by the sorting step in `_wrap_nodes_in_blockquote`.

        Args:
            indices: A list of integer indices of the nodes within their parent.
            parent_contents: The list of all child nodes of the common parent.

        Raises:
            ValueError: If the nodes are separated by any non-ignorable content.

        Mutations:
            None.

        Rules & Limits:
            - Sibling Invariant: The nodes corresponding to the indices must either
              be physically adjacent (e.g., indices [3, 4, 5]) or the gaps between
              their indices must be filled exclusively with ignorable nodes.
        """
        for a, b in itertools.pairwise(indices):
            if b - a > 1:  # There's a gap between the nodes.
                intervening_nodes = parent_contents[a + 1 : b] # pyright: ignore[reportUnknownArgumentType]
                assert self.config is not None
                if non_ignorable_nodes := [
                    node for node in intervening_nodes if not is_ignorable_node(node, self.config)
                ]:
                    formatted_intervening = [
                        self._format_node_for_log(n) for n in non_ignorable_nodes
                    ]
                    log.critical(
                        "Blockquote wrapping failed due to a contract violation: a strategy passed a "
                        "list of nodes that are not consecutive and are separated by non-ignorable "
                        "content. Indices: %s. Intervening nodes: %s",
                        indices,
                        formatted_intervening,
                    )
                    raise ValueError(
                        "Nodes to be wrapped in a blockquote must be consecutive or separated only by ignorable nodes.",
                    )
