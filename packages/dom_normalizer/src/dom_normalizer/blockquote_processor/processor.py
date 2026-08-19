"""Orchestrates the reconstruction of semantic blockquotes from plain paragraphs."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any

from bs4 import BeautifulSoup, Tag

from ..core import BookStyleContext, PipelineStatus
from ..core.component_registry import register_processor_factory
from ..core.dom_utils import generate_processor_metadata
from .base_strategy import BaseBlockquoteStrategy
from .epigraph_strategy import EpigraphStrategy
from .foreign_block_strategy import ForeignBlockStrategy
from .poetic_quote_strategy import PoeticQuoteStrategy
from .prose_quote_strategy import ProseQuoteStrategy

if TYPE_CHECKING:
    from ..core import BookStyleContext

log = logging.getLogger(__name__)


@register_processor_factory("blockquote_processor")
def create_blockquote_processor(
    context: BookStyleContext,
    **kwargs: Any,
) -> BlockquoteProcessor:
    """Factory function to create a BlockquoteProcessor instance with its strategies."""
    strategies = [
        EpigraphStrategy(),
        PoeticQuoteStrategy(),
        ProseQuoteStrategy(),
        ForeignBlockStrategy(),
    ]
    # This assumes BlockquoteProcessor's __init__ is `(self, context, strategies)`
    return BlockquoteProcessor(context, strategies=strategies)


class StrategyError(Exception):
    """Raised by strategies for expected, recoverable failures."""


class BlockquoteProcessor:
    """Orchestrates the reconstruction of semantic blockquotes from plain paragraphs.

    This processor uses a priority-based cascade of strategies to detect and
    wrap text blocks that are functionally blockquotes but are not marked as such.
    It iterates through the document's paragraphs, applying the first valid
    strategy from the cascade to prevent multiple transformations on the same content.

    Attributes:
        context (BookStyleContext): The shared context for the book.
        generic_quotes_created_count (int): A counter for the number of generic blockquotes created.
        epigraphs_identified_count (int): A counter for the number of epigraphs identified.
        _strategies (list[BaseBlockquoteStrategy]): The ordered list of detection strategies.
    """

    def __init__(
        self,
        context: BookStyleContext,
        strategies: Sequence[BaseBlockquoteStrategy],
    ) -> None:
        """Initializes the BlockquoteProcessor.

        Sets up the processing context, initializes state counters, and sets
        the detection strategies.

        Mutations:
            - Initializes instance variables for state tracking:
              `quotes_created_count` and `epigraphs_identified_count`.
            - Populates `self._strategies` with the provided strategies.
            - Binds the strategies to this processor instance.

        Rules & Limits:
            - Instance Lifecycle: Assumes this instance is scoped to a single book,
              per Global Directive #3.
        """
        self.context = context
        self.generic_quotes_created_count: int = 0
        self.epigraphs_identified_count: int = 0
        self.foreign_blocks_identified_count: int = 0
        self._strategies: Sequence[BaseBlockquoteStrategy] = strategies
        for strategy in self._strategies:
            strategy.processor = self
            strategy.context = context
            strategy.config = context.config

    def _is_paragraph_like(self, node: Tag) -> bool:
        """Checks if a node is a paragraph or a div that acts like one.

        A div is considered "paragraph-like" if it does not contain other
        common block-level elements, suggesting it is a direct text container
        rather than a structural wrapper.

        Args:
            node: The BeautifulSoup Tag to inspect.

        Returns:
            True if the node is a `<p>` or a paragraph-like `<div>`.
        """
        if node.name == "p":
            return True
        if node.name == "div":
            # A div is not paragraph-like if it contains other block elements.
            if node.find(
                self.context.config.blockquote_paragraph_like_blocking_tags,
                recursive=False,
            ):
                return False
            # It should also contain some non-whitespace text to be considered.
            return bool(node.get_text(strip=True))
        return False

    def process(self, soup: BeautifulSoup) -> tuple[BeautifulSoup, Mapping[str, Any]]:
        """Scans the DOM and applies blockquote reconstruction strategies.

        This is the main entry point for the processor. It iterates through all
        paragraph-like elements in the document, applying the priority cascade of
        strategies to each one. Once a strategy successfully processes a group of
        nodes, those nodes are marked as processed and skipped in subsequent
        iterations to prevent conflicts.

        Args:
            soup (BeautifulSoup): The in-memory DOM of the document to be processed.

        Returns:
            A tuple containing the mutated soup and the processing metadata.

        Mutations:
            - The input `soup` object is modified in-place by the applied strategies.

        Rules & Limits:
            - Code Shield: The processor immediately bypasses any node for which
              `self.context.is_inside_code_block(node)` returns `True`.
            - Execution Precedence: This module must run after `structural_sanitizer` and
              before line-unwrapping operations.
            - Traversal: Iterates over all paragraph-like elements (`<p>` and
              certain `<div>` tags) in the document.
            - State Management: Maintains a set of processed nodes to avoid
              re-evaluating nodes that have already been wrapped in a `<blockquote>`.
            - Full depth traversal: Yes.
        """
        processed_nodes: set[Tag] = set()
        # A static tuple is created to ensure safe iteration while modifying the DOM.
        for node in tuple(soup.find_all(["p", "div"])):
            # Filter for nodes that are paragraph-like to avoid processing
            # large, structural divs.
            if self._is_paragraph_like(node) and not self.context.is_inside_code_block(
                node,
            ):
                self._apply_strategies_to_node(node, soup, processed_nodes)

        # A run is successful if any quotes of any type were created.
        has_changes = (
            self.generic_quotes_created_count > 0
            or self.epigraphs_identified_count > 0
            or self.foreign_blocks_identified_count > 0
        )
        status = PipelineStatus.SUCCESS if has_changes else PipelineStatus.SUCCESS_NOOP
        return soup, self.get_metadata(status)

    def _validate_strategy_sequence(
        self,
        sequence: Any,
        strategy_name: str,
    ) -> None:
        """Validates that a strategy returns a valid sequence of Tag instances."""
        if not isinstance(sequence, Sequence) or isinstance(
            sequence,
            (str, bytes),
        ):
            raise TypeError(
                f"Strategy {strategy_name} returned an invalid sequence "
                f"type: {type(sequence)}. Expected a non-string Sequence of Tag instances.",
            )

        if invalid_elements := [
            (index, type(element))
            for index, element in enumerate(sequence)
            if not isinstance(element, Tag)
        ]:
            details = ", ".join(
                f"index {idx}: {elem_type}" for idx, elem_type in invalid_elements
            )
            raise TypeError(
                f"Strategy {strategy_name} returned a sequence containing "
                f"non-Tag elements ({details}). Expected all elements to be Tag instances.",
            )

    def _apply_strategies_to_node(
        self,
        node: Tag,
        soup: BeautifulSoup,
        processed_nodes: set[Tag],
    ) -> None:
        """Applies the strategy cascade to a single node, handling exceptions.

        Args:
            node (Tag): The node to process.
            soup (BeautifulSoup): The root DOM object.
            processed_nodes (set[Tag]): A set of Tag objects that have already
                been processed to avoid re-evaluation.
        """
        if node in processed_nodes or self.context.is_inside_code_block(node):
            return

        for strategy in self._strategies:
            try:
                if processed_sequence := strategy.find_and_apply(
                    node,
                    self.context,
                    soup,
                ):
                    self._validate_strategy_sequence(
                        processed_sequence,
                        strategy.__class__.__name__,
                    )
                    processed_nodes.update(processed_sequence)
                    break  # Strategy applied, move to the next node
            except StrategyError as e:
                # Log recoverable, strategy-level errors and continue.
                log.warning(
                    "Recoverable strategy error in %s, continuing: %s",
                    strategy.__class__.__name__,
                    e,
                )
            except Exception as e:  
                # Do not intercept interpreter-exiting exceptions.
                if isinstance(e, (KeyboardInterrupt, SystemExit)):
                    raise
                # For all other unexpected errors, log as critical and continue
                log.critical(
                    "Unexpected error in strategy %s, continuing: %s",
                    strategy.__class__.__name__,
                    e,
                    exc_info=True,
                )
                continue

    def get_metadata(self, status: PipelineStatus) -> Mapping[str, Any]:
        """Constructs the metadata dictionary for the processing results.

        Args:
            status (PipelineStatus): The final status of the pipeline run
                ('success', 'idle', or 'error').

        Returns:
            A dictionary containing the processing metadata.

        Mutations:
            None.

        Rules & Limits:
            - Output Contract: The returned dictionary must contain the following keys:
              - `blockquotes_reconstructed`: Total number of `<blockquote>` elements created.
              - `epigraphs_isolated`: Number of epigraphs identified.
              - `foreign_blocks_identified`: Number of foreign language blocks identified.
              - `status`: The final `PipelineStatus`.
              - `execution_timestamp`: An ISO 8601 timestamp.
        """
        return generate_processor_metadata(
            processor_key="blockquote_processing",
            status=status,
            blockquotes_reconstructed=self.generic_quotes_created_count
            + self.epigraphs_identified_count
            + self.foreign_blocks_identified_count,
            epigraphs_isolated=self.epigraphs_identified_count,
            foreign_blocks_identified=self.foreign_blocks_identified_count,
        )
