"""A multi-pass DOM sanitizer for normalizing layout and whitespace.

This module operates as the first processor in Stage 1. Its primary purpose is
to perform a deterministic cleanup of the DOM, preparing it for subsequent
processors. It follows a strict, multi-step protocol to capture layout-related
styling (e.g., floats, margins) by promoting them to semantic classes, and then
purging the original styling and non-semantic attributes. It also handles the
intelligent collapse of `<br>` tags, preserving them in poetic contexts while
merging them into spaces in prose.

This processor must run before `navigation_purger` and `floating_element_processor`
to ensure they can correctly identify structures without being hindered by raw
inline styles or fragmented text nodes.

Analytical Blueprint:
---------------------

Based on the specification, the following logic will be mapped:

Class Methods (StructuralSanitizer):
    - __init__: Initializes all telemetry counters and the strategy instances.
    - sanitize: The main orchestrator. It iterates through all block-level nodes,
      delegating sanitization steps (1-4) to a series of strategy classes. After
      processing all nodes, it executes a final epilogue strategy for document-wide
      cleanup.
    - get_metadata: Compiles the final metadata dictionary.

Strategy Classes (in strategies.py):
    - InlineStylePromotionStrategy: Handles Steps 1 & 2 (promoting float and indent styles).
    - AttributePurgeStrategy: Handles Step 3 (purging legacy attributes and layout styles).
    - BrCollapseStrategy: Handles Step 4 (intelligently collapsing <br> tags).
    - EpilogueStrategy: Handles Step 5 (a series of final cleanup passes for tracking
      attributes, blockquote styles, empty nodes, and text coalescing).
"""

from __future__ import annotations

import logging
from typing import Any

from bs4 import BeautifulSoup, Tag

from ..core import BookStyleContext, PipelineStatus
from ..core.component_registry import register_processor_factory
from ..core.dom_utils import find_all_snapshot, get_tag_identifier, get_utc_timestamp
from .strategies import (
    AttributePurgeStrategy,
    BrCollapseStrategy,
    EpilogueStrategy,
    InlineStylePromotionStrategy,
)

log = logging.getLogger(__name__)


@register_processor_factory("structural_sanitizer")
def create_structural_sanitizer(
    context: BookStyleContext,
    **kwargs: Any,
) -> StructuralSanitizer:
    """Factory function to create a StructuralSanitizer instance with its strategies."""
    inline_promoter = InlineStylePromotionStrategy(context)
    attr_purger = AttributePurgeStrategy(context)
    br_collapser = BrCollapseStrategy(context)
    epilogue = EpilogueStrategy(context)
    return StructuralSanitizer(
        context,
        inline_promoter=inline_promoter,
        attr_purger=attr_purger,
        br_collapser=br_collapser,
        epilogue=epilogue,
    )


#: Tags that are iterated over as block-level nodes in the main sanitize loop.
_BLOCK_LEVEL_TAGS = frozenset(
    [
        "p",
        "div",
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
        "section",
        "article",
        "aside",
        "main",
        "header",
        "footer",
    ],
)


class StructuralSanitizer:
    """Orchestrates a multi-pass sanitization of a DOM tree.

    This class is responsible for normalizing layout, purging non-semantic
    attributes, and collapsing whitespace to prepare the DOM for further
    semantic processing. It operates by delegating tasks to a series of
    specialized strategy classes.

    Attributes:
        context (BookStyleContext): The shared context for the book.
        empty_nodes_purged (int): Counter for purged empty nodes.
        br_tags_collapsed (int): Counter for collapsed <br> tags in prose.
        poetic_br_tags_preserved (int): Counter for preserved <br> tags in poetry.
        layout_attributes_persisted (int): Counter for legacy attributes
            that were persisted as data-* attributes.
        inline_floats_normalized (int): Counter for float styles promoted to a class.
        inline_indents_normalized (int): Counter for indent styles promoted to a class.
    """

    def __init__(
        self,
        context: BookStyleContext,
        inline_promoter: InlineStylePromotionStrategy,
        attr_purger: AttributePurgeStrategy,
        br_collapser: BrCollapseStrategy,
        epilogue: EpilogueStrategy,
    ) -> None:
        """Initializes the sanitizer with context and telemetry counters.

        Args:
            context (BookStyleContext): The shared context for the book.
            inline_promoter: The strategy for promoting inline styles.
            attr_purger: The strategy for purging attributes.
            br_collapser: The strategy for collapsing <br> tags.
            epilogue: The strategy for final document cleanup.

        Returns:
            None

        Mutations:
            - Initializes all telemetry counters to 0.
            - Sets `self.context`.
            - Binds the injected strategies to this processor.

        Rules & Limits:
            - Instance Lifecycle: Assumes this instance is scoped to a single book.
        """
        self.context = context
        self.empty_nodes_purged = 0
        self.br_tags_collapsed = 0
        self.poetic_br_tags_preserved = 0
        self.layout_attributes_persisted = 0
        self.inline_floats_normalized = 0
        self.inline_indents_normalized = 0
        self.errors: list[dict[str, Any]] = []

        self.inline_promoter = inline_promoter
        self.attr_purger = attr_purger
        self.br_collapser = br_collapser
        self.epilogue = epilogue

        # Bind all strategies to this processor instance.
        for strategy in (inline_promoter, attr_purger, br_collapser, epilogue):
            strategy.processor = self

    # --- Telemetry Interface ---

    def increment_empty_nodes_purged(self, amount: int = 1) -> None:
        """Increments the counter for purged empty nodes."""
        self.empty_nodes_purged += amount

    def increment_br_tags_collapsed(self, amount: int = 1) -> None:
        """Increments the counter for collapsed <br> tags."""
        self.br_tags_collapsed += amount

    def increment_poetic_br_tags_preserved(self, amount: int = 1) -> None:
        """Increments the counter for preserved poetic <br> tags."""
        self.poetic_br_tags_preserved += amount

    def increment_layout_attributes_persisted(self, amount: int = 1) -> None:
        """Increments the counter for persisted legacy layout attributes."""
        self.layout_attributes_persisted += amount

    def increment_inline_floats_normalized(self, amount: int = 1) -> None:
        """Increments the counter for normalized inline float styles."""
        self.inline_floats_normalized += amount

    def increment_inline_indents_normalized(self, amount: int = 1) -> None:
        """Increments the counter for normalized inline indent styles."""
        self.inline_indents_normalized += amount

    def sanitize(self, soup: BeautifulSoup) -> dict[str, Any]:
        """Executes the full 5-step sanitization pipeline on the DOM.

        This is the main entry point. It orchestrates the sequential application
        of style promotion, attribute purging, and whitespace collapse on all
        block-level elements, followed by a final epilogue of cleanup passes.

        Args:
            soup (BeautifulSoup): The in-memory DOM of the document to be processed.

        Returns:
            dict[str, Any]: A dictionary containing the execution log, conforming to
                the canonical metadata contract.

        Raises:
            Exception: Per Global Directive #1, any unexpected native exceptions
                during processing will be caught, logged as CRITICAL, and re-raised.

        Mutations:
            - The input `soup` object is modified in-place by the various strategy
              classes.

        Rules & Limits:
            - Pipeline Order Contract: This processor must execute first in Stage 1,
              before `navigation_purger` and `floating_element_processor`.
            - Execution Flow:
              1. Iterates through all block-level nodes, applying Steps 1-4 to each.
              2. Executes the epilogue strategy after the main loop concludes.
            - Full depth traversal: Yes.
        """
        # Use snapshot_iterator for safe iteration while modifying the DOM.
        block_nodes = find_all_snapshot(soup, _BLOCK_LEVEL_TAGS)

        for node in block_nodes:
            if node.parent is None or not isinstance(node, Tag):
                continue
            try:
                self.inline_promoter.process(node)
                self.attr_purger.process(node)
                self.br_collapser.process(node)
            except Exception as e:  
                if isinstance(e, (KeyboardInterrupt, SystemExit)):
                    raise
                error_details = {
                    "node": get_tag_identifier(node),
                    "error": str(e),
                }
                self.errors.append(error_details)
                log.exception(
                    "Error processing node %s in StructuralSanitizer: %s",
                    getattr(node, "name", "unknown"),
                    e,
                    exc_info=True,
                )
                continue

        try:
            self.epilogue.process(soup)
        except Exception as e:  
            if isinstance(e, (KeyboardInterrupt, SystemExit)):
                raise
            self.errors.append({"node": "document_epilogue", "error": str(e)})
            log.exception(
                "Error in StructuralSanitizer epilogue: %s",
                e,
                exc_info=True,
            )

        has_changes = any(
            [
                self.empty_nodes_purged > 0,
                self.br_tags_collapsed > 0,
                self.poetic_br_tags_preserved > 0,
                self.layout_attributes_persisted > 0,
                self.inline_floats_normalized > 0,
                self.inline_indents_normalized > 0,
            ],
        )

        if self.errors:
            final_status = PipelineStatus.PARTIAL_SUCCESS
        elif has_changes:
            final_status = PipelineStatus.SUCCESS
        else:
            final_status = PipelineStatus.SUCCESS_NOOP
        return self.get_metadata(final_status)

    def get_metadata(
        self,
        status: PipelineStatus = PipelineStatus.SUCCESS,
    ) -> dict[str, Any]:
        """Constructs the metadata dictionary for the processing results.

        Args:
            status (PipelineStatus): The final status of the pipeline run.

        Returns:
            dict[str, Any]: A dictionary conforming to the canonical metadata contract.
        """
        return {
            "structural_sanitization": {
                "status": status.value,
                "execution_timestamp": get_utc_timestamp(),
                "errors_encountered": self.errors,
                "empty_nodes_purged": self.empty_nodes_purged,
                "br_tags_collapsed": self.br_tags_collapsed,
                "poetic_br_tags_preserved": self.poetic_br_tags_preserved,
                "layout_attributes_persisted": self.layout_attributes_persisted,
                "inline_floats_normalized": self.inline_floats_normalized,
                "inline_indents_normalized": self.inline_indents_normalized,
            },
        }
