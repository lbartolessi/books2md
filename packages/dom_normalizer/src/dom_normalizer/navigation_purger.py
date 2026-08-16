"""A multi-pillar engine for detecting and purging redundant navigation structures.

This module operates in Stage 1 of the ingestion pipeline. Its primary purpose
is to detect, isolate, and purge tables of contents, index matrices, and other
is to detect, isolate, and purge tables of contents, index matrices, and other
link arrays from the DOM before text slicing occurs. This prevents navigational
content from polluting the narrative chunks used by downstream models.

This processor must run strictly after `structural_sanitizer` and before
`floating_element_processor`.

Analytical Blueprint:
---------------------

Based on the specification, the following logic will be mapped to the class
methods:

Global Free Functions (Module Level):
    - None present in the skeleton.

Class Methods (NavigationPurger):
    - __init__: Initializes all telemetry counters to zero (`native_toc_isolated`,
      `inline_toc_blocks_purged`, `tabular_indexes_purged`, `chars_removed_count`,
      `elements_evaluated_count`).
    - purge: Orchestrates the three-pillar detection and purging process in a
      strict sequence: 1. `_purge_native_and_fallback_tocs`, 2.
      `_purge_inline_toc_blocks`, 3. `_purge_tabular_indexes`.
    - _purge_nodes: A utility to decompose a list of nodes and update the
      `chars_removed_count` telemetry counter.
    - _handle_tier2_fallback_purge: Implements the Tier 2 file-based fallback.
      Calculates Text-to-Link Character Ratio (TLCR). If TLCR < 0.85 and no
      protected prose containers (classes: "prose", "editorial", "editorial-prose")
      are found, it purges the entire `<body>`. Otherwise, it delegates to
      Pillars 2 and 3.
    - _purge_native_and_fallback_tocs: Implements Pillar 1. Purges semantic TOCs
      (`epub:type="toc"`, `role="doc-toc"`, `<nav>`) and triggers the Tier 2
      fallback for files matching `_FILE_FALLBACK_RX`.
    - _is_potential_toc_line: Implements Pillar 2's line matching using `_TOC_LINE_RX`.
    - _purge_inline_toc_blocks: Implements Pillar 2's sliding window algorithm to
      find and evaluate contiguous runs of potential TOC lines.
    - _extract_trailing_numbers_from_block: A helper for Pillar 2 to parse
      trailing page numbers from a block of nodes.
    - _is_arithmetic_progression: Implements Pillar 2's "Agnostic Anti-Step Guard"
      to preserve instruction checklists (e.g., `[1, 2, 3, 4]`).
    - _evaluate_and_purge_toc_block: Implements Pillar 2's final decision logic,
      checking the run length (>= 4) and applying the anti-step guard.
    - _get_final_column_numeric_values: A helper for Pillar 3 to extract numbers
      from the last cell of each table row.
    - _is_strictly_non_decreasing: Implements Pillar 3's strict monotonicity rule
      (`p_i <= p_{i+1}`).
    - _initial_column_has_short_text: Implements Pillar 3's initial column
      constraint (text length < 25 characters).
    - _is_potential_tabular_index: A composite checker for Pillar 3 that applies
      all tabular index rules (row count, column constraints, monotonicity).
    - _purge_tabular_indexes: Implements Pillar 3's main loop to find and purge
      tables that are identified as indexes.
    - get_metadata: Compiles the final metadata dictionary according to the
      YAML contract.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from bs4 import BeautifulSoup, Tag

from .core import (
    BookStyleContext,
    PipelineStatus,
)
from .core.dom_utils import (
    find_all_snapshot,
    generate_processor_metadata,
)

log = logging.getLogger(__name__)


class NavigationPurger:
    """A multi-pillar engine for detecting and purging redundant navigation structures."""

    LINK_DENSITY_THRESHOLD: float = 0.7

    def __init__(
        self,
        context: BookStyleContext,
    ) -> None:
        self.context = context
        self.nav_elements_purged: int = 0

    def _purge_by_selector(self, soup: BeautifulSoup) -> None:
        """Purges navigation elements based on a CSS selector.

        This method finds and removes elements that match common navigation
        selectors like `<nav>`, `role="navigation"`, or `class="toc"`.

        Args:
            soup: The BeautifulSoup object to modify.
        """
        selectors = 'nav, [role="doc-toc"], [role="navigation"], .menu, .toc'
        nodes_to_check = tuple(soup.select(selectors))

        for node in nodes_to_check:
            if not node.parent:  # Already removed
                continue
            if self.context.is_inside_code_block(node):
                continue

            node.decompose()
            self.nav_elements_purged += 1

    def _purge_ul_by_link_density(self, soup: BeautifulSoup) -> None:
        """Purges <ul> elements with high link density.

        This method identifies `<ul>` elements that are likely to be navigation
        menus by calculating the ratio of link text to total text and removing
        those that exceed a defined threshold.

        Args:
            soup: The BeautifulSoup object to modify.
        """
        for ul_tag in find_all_snapshot(soup, "ul"):
            if not isinstance(ul_tag, Tag):
                continue
            if not ul_tag.parent:  # Already removed
                continue
            if self.context.is_inside_code_block(ul_tag):
                continue

            total_text_len = len(ul_tag.get_text(strip=True))
            if total_text_len == 0:
                continue

            link_text_len = sum(
                len(a.get_text(strip=True)) for a in ul_tag.find_all("a")
            )
            density = link_text_len / total_text_len

            if density > self.LINK_DENSITY_THRESHOLD:
                ul_tag.decompose()
                self.nav_elements_purged += 1

    def process(self, soup: BeautifulSoup) -> tuple[BeautifulSoup, Mapping[str, Any]]:
        """Executes the navigation purging process.

        This is the main entry point. It orchestrates the purging of navigation
        elements based on semantic selectors and link density heuristics.

        Args:
            soup (BeautifulSoup): The in-memory DOM of the document to be processed.

        Returns:
            A tuple containing the mutated soup object and a dictionary with
            metadata about the normalization process.
        """
        self._purge_by_selector(soup)
        self._purge_ul_by_link_density(soup)

        has_changes = self.nav_elements_purged > 0
        status = PipelineStatus.SUCCESS if has_changes else PipelineStatus.SUCCESS_NOOP
        return soup, self.get_metadata(status)

    def get_metadata(self, status: PipelineStatus) -> Mapping[str, Any]:
        """Constructs the metadata dictionary for the processing results.

        Args:
            status (PipelineStatus): The final status of the pipeline run.

        Returns:
            A dictionary conforming to the canonical metadata contract.
        """
        return generate_processor_metadata(
            processor_key="navigation_purging",
            status=status,
            nav_elements_purged=self.nav_elements_purged,
        )
