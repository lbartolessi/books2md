"""A structural reconstruction and consolidation engine for semantic lists.

This module operates as a Stage 2 processor. Its purpose is to identify and
reconstruct list-like structures from sequences of plain paragraphs (`<p>`) and
to sanitize and consolidate existing list elements (`<ul>`, `<ol>`).

This processor must run after `table_normalizer` to prevent misidentification
of tabular data and before `blockquote_processor`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from bs4 import BeautifulSoup

from ..core import BookStyleContext, PipelineStatus
from ..core.component_registry import register_processor_factory
from ..core.dom_utils import generate_processor_metadata
from .strategies import (
    BaseListStrategy,
    FusionStrategy,
    ReconstructionStrategy,
    SanitizationStrategy,
)


@register_processor_factory("lists")
def create_list_normalizer(context: BookStyleContext, **kwargs: Any) -> ListNormalizer:
    """Factory function to create a ListNormalizer instance with its strategies."""
    strategies = [
        ReconstructionStrategy(),
        FusionStrategy(),
        SanitizationStrategy(),
    ]
    # This assumes ListNormalizer's __init__ is `(self, context, strategies)`
    return ListNormalizer(context, strategies=strategies)


class ListNormalizer:
    """A structural reconstruction and consolidation engine for semantic lists.

    This processor operates in three distinct suites to heal list structures:
    1.  **Reconstruction:** Identifies sequences of plain paragraphs that use
        textual prefixes (e.g., "1.", "*") or vendor-specific CSS classes to
        simulate lists and reconstructs them into semantic `<ul>` and `<ol>`
        elements. This includes handling nested lists and multi-line items.
    2.  **Sanitization:** Scans existing `<ul>` and `<ol>` tags for children that
        are not `<li>` elements ("orphans") and wraps them in `<li>` tags to
        ensure XHTML validity.
    3.  **Fusion:** Finds and merges adjacent lists of the same type that are
        separated only by non-semantic noise (e.g., `<br>` tags), creating
        a single, continuous list.

    The processor maintains a set of processed nodes to prevent re-evaluation,
    ensuring that each paragraph is considered for list conversion only once.

    Attributes:
        context (BookStyleContext): The shared context for the book.
        unordered_lists_recovered (int): A counter for the number of `<ul>`
            lists reconstructed from paragraphs.
        ordered_lists_recovered (int): A counter for the number of `<ol>`
            lists reconstructed from paragraphs.
        multiline_items_welded (int): A counter for continuation paragraphs
            merged into a single list item.
        total_raw_paragraphs_purged (int): A counter for the total number of
            source paragraphs converted into list items.
        lists_fused (int): A counter for the number of adjacent lists that
            were merged.
    """

    def __init__(
        self,
        context: BookStyleContext,
        strategies: Sequence[BaseListStrategy],
    ) -> None:
        """Initializes the list normalizer with context and telemetry counters.

        Telemetry counters are grouped by suite:
        - Reconstruction: unordered_lists_recovered, ordered_lists_recovered, multiline_items_welded
        - Sanitization: total_raw_paragraphs_purged, lists_sanitized
        - Fusion: lists_fused
        """
        self.context = context
        self.unordered_lists_recovered: int = 0
        self.ordered_lists_recovered: int = 0
        self.multiline_items_welded: int = 0
        self.total_raw_paragraphs_purged: int = 0
        self.lists_sanitized: int = 0
        self.lists_fused: int = 0
        self.strategies = strategies
        for strategy in self.strategies:
            strategy.processor = self
            strategy.context = self.context
            strategy.config = self.context.config

    def process(self, soup: BeautifulSoup) -> tuple[BeautifulSoup, Mapping[str, Any]]:
        """Orchestrates the three-suite list normalization process.

        This is the main entry point. It executes a series of transformations to
        reconstruct, sanitize, and fuse lists within the document. The process
        is carefully ordered to ensure correctness.

        Args:
            soup (BeautifulSoup): The in-memory DOM of the document to be processed.

        Returns:
            A tuple containing the mutated soup object and a metadata dictionary.
        """
        for strategy in self.strategies:
            strategy.process(soup)

        has_changes = (
            self.unordered_lists_recovered > 0
            or self.ordered_lists_recovered > 0
            or self.multiline_items_welded > 0
            or self.lists_fused > 0
            or self.lists_sanitized > 0
        )
        status = PipelineStatus.SUCCESS if has_changes else PipelineStatus.SUCCESS_NOOP

        return soup, self._get_metadata(status)

    def _get_metadata(self, status: PipelineStatus) -> Mapping[str, Any]:
        """Constructs the metadata dictionary for the processing results.

        Args:
            status (PipelineStatus): The final status of the pipeline run.

        Returns:
            Mapping[str, Any]: A dictionary conforming to the output contract.
        """
        return generate_processor_metadata(
            processor_key="list_normalization",
            status=status,
            unordered_lists_recovered=self.unordered_lists_recovered,
            ordered_lists_recovered=self.ordered_lists_recovered,
            multiline_items_welded=self.multiline_items_welded,
            total_raw_paragraphs_purged=self.total_raw_paragraphs_purged,
            lists_fused=self.lists_fused,
            lists_sanitized=self.lists_sanitized,
        )
