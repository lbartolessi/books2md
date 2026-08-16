"""A strategy for footnotes marked with explicit DPUB-ARIA and EPUB3 semantics.

This module provides the `AriaDpubStrategy`, a high-priority (Stage A) strategy
that processes footnotes and endnotes based on explicit semantic markers like
`role="doc-footnote"` or `epub:type="noteref"`. It is designed to be the
authoritative handler for these standard accessibility vocabularies, processing
them with high confidence and without heuristic inference.

Analytical Blueprint:
---------------------
- **Objective:** To identify and normalize footnote structures that are explicitly
  marked up using standard DPUB-ARIA roles or EPUB3 `epub:type` attributes.
- **Components:**
  - `AriaDpubStrategy`: The main class implementing the strategy.
  - `can_process`: Scans the DOM for the presence of specific ARIA roles or
    `epub:type` attributes related to footnotes and endnotes.
  - `process`: Orchestrates the normalization by extracting, standardizing, and
    rebuilding the footnote section using the common helpers from the base class.
- **Analytical Steps:**
  1. Scan the DOM for callouts using the selector `a[epub:type="noteref"],
     a[role="doc-noteref"]`, etc.
  2. Scan the DOM for note bodies using the selector `aside[epub:type="footnote"],
     [role="doc-footnote"]`, etc.
  3. Extract all note bodies from the DOM, keying them by their `id`.
  4. Iterate through all callouts, matching them to the extracted bodies via
     their `href` attribute.
- **Transformation Rules:**
  - Matched callouts and bodies are standardized using the helpers from
    `BaseFootnoteStrategy`.
  - Callouts are converted to a canonical `<a role="doc-noteref">` format.
  - Note bodies are converted to canonical `<li>` elements.
  - Backlinks (`<a role="doc-backlink">`) are synthesized if missing.
  - All processed `<li>` notes are appended to a single, standardized
    `<section role="doc-endnotes"><ol>...</ol></section>` at the end of the document.
  - Original note body containers (e.g., `<aside>`) are removed.
- **Output:**
  - A mutated `BeautifulSoup` object with a standardized footnote section.
  - A metadata dictionary reporting the strategy name, status, and note count.
"""

import logging
from typing import Any, ClassVar

from bs4 import BeautifulSoup, Tag

from dom_normalizer.core import BookStyleContext, PipelineStatus
from dom_normalizer.core.dom_utils import get_utc_timestamp

from .base_strategy import AnomalyCollector, AnomalyKey, BaseFootnoteStrategy

log = logging.getLogger(__name__)


class AriaDpubStrategy(BaseFootnoteStrategy):
    """A high-priority static strategy (Stage A) for DPUB-ARIA and EPUB3 markers.

    This class is the exclusive owner of the accessibility vocabulary related
    to footnotes and endnotes throughout the pipeline. It intercepts and processes
    elements based on explicit semantic declarations from the author or
    publishing software, ignoring any heuristic inference.

    Invariants:
        - No other module (such as accessibility_normalizer) should operate on
          'doc-footnote' or 'doc-noteref' roles.
        - The mutation must maintain the structural hierarchy by injecting the
          necessary attributes and relocating nodes without destroying their
          internal content.
    """

    BODY_SELECTORS: ClassVar[tuple[str, ...]] = (
        'aside[epub\\:type~="footnote"]',
        'aside[epub\\:type~="endnote"]',
        '[role~="doc-footnote"]',
        '[role~="doc-endnote"]',
    )
    CALLOUT_SELECTORS: ClassVar[tuple[str, ...]] = (
        'a[epub\\:type~="noteref"]',
        'a[epub\\:type~="endnoteref"]',
        'a[role~="doc-noteref"]',
        'a[role~="doc-endnoteref"]',
    )
    BACKLINK_SELECTOR: ClassVar[str] = 'a[role="doc-backlink"]'

    def __init__(self) -> None:
        """Initializes the AriaDpubStrategy."""
        super().__init__()
        self.body_selector = ", ".join(self.BODY_SELECTORS)
        self.callout_selector = ", ".join(self.CALLOUT_SELECTORS)
        self.backlink_selector = self.BACKLINK_SELECTOR  # NOSONAR

    def can_process(self, soup: BeautifulSoup, context: BookStyleContext) -> bool:
        """
        Evaluates if the DOM resource contains explicit semantic note markers.

        Searches for the presence of any of the following selectors in the DOM tree:
        - EPUB3 attributes: `epub:type="footnote"`, `epub:type="noteref"`
        - ARIA attributes: `role="doc-footnote"`, `role="doc-noteref"`, `role="doc-backlink"`

        Args:
            soup (BeautifulSoup): The instantiated DOM tree of the XHTML source file.
            context (BookStyleContext): The global style and configuration context for the book.

        Returns:
            bool: True if at least one explicit semantic marker is found; False otherwise.
        """
        selectors_to_check = (
            self.BODY_SELECTORS + self.CALLOUT_SELECTORS + (self.BACKLINK_SELECTOR,)
        )
        return any(soup.select_one(s) for s in selectors_to_check)

    def _extract_aria_note_bodies(
        self,
        soup: BeautifulSoup,
        collector: AnomalyCollector,
    ) -> dict[str, Tag]:
        """Extracts note bodies, filtering out any that are already in the canonical format."""
        note_bodies = {}
        for body in soup.select(self.body_selector):
            # Skip bodies that are already in the canonical endnotes section to ensure idempotency.
            if body.name == "li" and body.find_parent(
                "section",
                attrs={"role": "doc-endnotes"},
            ):
                continue

            raw_id = body.get("id")
            if isinstance(raw_id, str) and raw_id.strip():
                note_id = raw_id.strip()
                if note_id in note_bodies:
                    collector.add(
                        key=AnomalyKey.DUPLICATE_ID,
                        message=f"Duplicate note body ID '#{note_id}' found. Keeping the first instance.",
                        payload={"tag_html": str(body)[:100]},
                    )
                    continue
                note_bodies[note_id] = body.extract()
            else:
                # This covers cases where 'id' is missing, empty, or not a string.
                collector.add(
                    key=AnomalyKey.CONFIG_ERROR,
                    message="Found a potential note body that lacks a valid 'id' attribute and will be ignored.",
                    payload={"tag_html": str(body)[:100]},
                )
        return note_bodies

    def _run_processing_workflow(
        self,
        soup: BeautifulSoup,
        collector: AnomalyCollector,
        start_time: str,
    ) -> tuple[BeautifulSoup, dict[str, Any]]:
        """Orchestrates the main processing logic and returns final metadata."""
        notes_count = 0

        note_bodies = self._extract_aria_note_bodies(soup, collector)
        processed_notes, notes_count, used_ids = self._process_callouts(
            soup,
            note_bodies,
            collector,
        )

        # Handle any remaining (unlinked) note bodies.
        orphan_ids = set(note_bodies.keys()) - used_ids
        for orphan_id in orphan_ids:
            collector.add(
                key=AnomalyKey.ORPHAN_NOTE,
                message=f"Note body '#{orphan_id}' was found but not referenced.",
            )

        self._rebuild_notes_section(soup, processed_notes)

        # Determine final status
        if collector.anomalies:
            status = (
                PipelineStatus.PARTIAL_SUCCESS
                if notes_count > 0
                else PipelineStatus.ERROR
            )
        elif notes_count > 0:
            status = PipelineStatus.SUCCESS
        else:
            status = PipelineStatus.SUCCESS_NOOP

        notes_found_count = len(note_bodies)
        notes_rebuilt_count = len(processed_notes)
        backlinks_injected_count = notes_count
        anomalies_repaired_count = len(collector.anomalies)
        return soup, BaseFootnoteStrategy.create_metadata(
            strategy_name="AriaDpubStrategy",
            status=status,
            notes_processed_count=backlinks_injected_count,
            notes_found_count=notes_found_count,
            notes_rebuilt_count=notes_rebuilt_count,
            backlinks_injected_count=backlinks_injected_count,
            anomalies=collector.to_list(),
            anomalies_repaired_count=anomalies_repaired_count,
            start_time=start_time,
        )

    def process(
        self,
        soup: BeautifulSoup,
        context: BookStyleContext,
        all_soups: dict[str, BeautifulSoup] | None = None,
        current_soup_key: str | None = None,
    ) -> tuple[BeautifulSoup, dict[str, Any]]:
        """Orchestrates the isolation, reordering, and standardization of footnotes.

        This method acts as the main entry point for the AriaDpubStrategy. It
        orchestrates the entire process of identifying, extracting, standardizing,
        and rebuilding footnote structures based on DPUB-ARIA and EPUB3 semantics.

        Args:
            soup (BeautifulSoup): The DOM tree to mutate.
            context (BookStyleContext): The shared context for the book.

        Returns:
            tuple[BeautifulSoup, dict[str, Any]]:
                - BeautifulSoup: The mutated DOM tree.
                - dict: Metadata about the processing, including status, anomalies,
                  and the count of processed notes.
                    {
                        "footnote_processing": {
                            "strategy_applied": "AriaDpubStrategy",
                            "processing_status": "<status>",
                            "anomalies_detected": [],
                            "notes_count": <int>,
                            "execution_timestamp": "<iso-8601 UTC>"
                        }
                    }

        Raises:
            Exception: Per Global Directive #1, any unexpected native exceptions
                during processing will be caught, logged as CRITICAL, and re-raised.


        Mutations:
            - The input `soup` object is modified in-place by the various helper
              methods.

        Rules & Limits:
            - Orchestration: This method calls a sequence of private helper methods
              to perform its tasks, ensuring a clear separation of concerns.

        Calls:
            - `_extract_aria_note_bodies`: To get all note bodies.
            - `_process_callouts`: To match callouts with bodies and standardize them.
            - `_rebuild_notes_section`: To create a new, standardized footnote section.
            - `get_utc_timestamp`: To record the execution time.
        """
        # pylint: disable=unused-argument
        collector = AnomalyCollector()
        start_time = get_utc_timestamp() # AnomalyCollector is now public, so no need for _AnomalyCollector

        try:
            return self._run_processing_workflow(soup, collector, start_time)
        except Exception as e:
            log.critical(
                "Unexpected error in AriaDpubStrategy.process: %s",
                e,
                exc_info=True,
            )
            raise
