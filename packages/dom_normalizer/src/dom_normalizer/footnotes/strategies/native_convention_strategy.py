"""A strategy for formats with explicitly declared but incomplete note links.

This module provides the `NativeConventionFootnoteStrategy`, which targets native
markup conventions (like those in FB2) where footnote callouts are explicitly
marked (e.g., `<a type="note">`), but the corresponding note bodies may lack
the required backlinks for full navigability. The primary role of this strategy
is to synthesize these missing backlinks.

Analytical Blueprint:
---------------------
- **Objective:** To identify footnote systems that use a native, non-standard
  callout attribute (e.g., `type="note"`) and ensure they have complete
  bidirectional linking by injecting missing backlinks.
- **Components:**
  - `NativeConventionFootnoteStrategy`: The main class implementing the strategy.
  - `can_process`: Scans the DOM for the presence of `<a type="note">` tags.
  - `process`: Orchestrates the backlink synthesis process.
  - `_get_href`: Safely extracts the `href` from a callout tag.
  - `_inject_backlink`: Creates and appends a standard backlink to a note body.
  - `_process_callout`: Handles the logic for a single callout-body pair,
    including synthesizing a return ID for the callout.
- **Analytical Steps:**
  1. Scan the document for all callouts matching `a[type="note"]`.
  2. For each callout, determine the target note body's ID from its `href`.
  3. Locate the note body element, potentially searching in a separate "donor"
     document if `notes_file_key` is specified.
  4. Check if the note body already contains a backlink.
- **Transformation Rules:**
  - If a note body lacks a backlink, a new one is created and injected.
  - To create the backlink, a unique return ID of the format
    `fnref-{target_id}-{index}` is assigned to the callout `<a>` tag.
  - The new backlink (`<a role="doc-backlink">`) is created with an `href`
    pointing to this new callout ID.
  - Unresolved callouts (pointing to non-existent notes) are logged as anomalies.
- **Output:**
  - A mutated `BeautifulSoup` object where note bodies have guaranteed backlinks.
  - A metadata dictionary reporting the strategy name, status, and any anomalies.
"""

import logging
from collections.abc import Iterator
from enum import StrEnum
from typing import Any

from bs4 import BeautifulSoup, Tag

from dom_normalizer.core import BookStyleContext, PipelineStatus
from dom_normalizer.core.dom_utils import (
    get_utc_timestamp,
)

from .base_strategy import AnomalyKey, BaseFootnoteStrategy, normalize_href_attr

log = logging.getLogger(__name__)


class NativeConventionFootnoteStrategy(BaseFootnoteStrategy):
    """A strategy for formats with explicitly declared note locations.

    This strategy targets native conventions like FB2 or EPUB3 where the
    location of note bodies is explicitly declared (e.g., in a separate file
    or a specific section), but the bidirectional linking (backlinks) may be
    incomplete or absent. It identifies callouts via `a[type='note']` and
    synthesizes the necessary backlinks to ensure full navigability.

    Attributes:
        unresolved_targets (list[str]): A list for telemetry, storing `href`
            values of callouts that point to non-existent note bodies.
    """

    class _UnresolvedReason(StrEnum):
        """Defines reasons for unresolved footnote targets."""

        NON_FRAGMENT = "non-fragment"
        DANGLING = "dangling"

    def __init__(self, notes_file_key: str | None = None) -> None:
        """Initializes the strategy for formats with declared note locations.

        Args:
            notes_file_key (str | None): The key identifying the file within the
                book's resources that contains the note bodies. If None, notes
                are assumed to be in the same document.

        Returns:
            None

        Mutations:
            - Initializes `self.unresolved_targets` to an empty list for telemetry.
        """
        self.notes_file_key = notes_file_key
        super().__init__()
        self.backlink_selector = 'a[role="doc-backlink"]'
        self.unresolved_targets: list[
            tuple[
                NativeConventionFootnoteStrategy._UnresolvedReason,
                str,
                Tag,
            ]
        ] = []

    def _iter_note_callouts(self, soup: BeautifulSoup) -> Iterator[tuple[Tag, str]]:
        """Iterates over all potential note callouts in the soup.

        This helper centralizes the logic for finding `a[type="note"]` tags
        and ensuring they have a usable `href` attribute.
        """
        for callout in soup.find_all("a", attrs={"type": "note"}):
            href = self._get_href(callout)
            if href is not None:
                yield callout, href

    def can_process(self, soup: BeautifulSoup, context: BookStyleContext) -> bool:
        """Evaluates if the DOM contains native forward-only note callouts.

        Args:
            soup (BeautifulSoup): The DOM tree to evaluate.
            context (BookStyleContext): The shared context for the book.

        Raises:
            Exception: Per Global Directive #1, any unexpected native exceptions
                will be caught, logged as CRITICAL, and re-raised.

        Mutations:
            None.

        Rules & Limits:
            - Target Selector: `a[type="note"]`.
            - Full depth traversal: Yes.
        """
        try:
            # Use _iter_note_callouts to ensure consistency with process method
            return any(True for _ in self._iter_note_callouts(soup))
        except Exception:
            log.critical(
                "Unexpected error in NativeConventionFootnoteStrategy.can_process",
                exc_info=True,
            )
            raise

    def _get_href(self, callout: Tag) -> str | None:
        """Safely extracts and returns the href from a callout.

        Args:
            callout (Tag): The BeautifulSoup `Tag` representing the callout.

        Returns:
            str | None: The extracted href string, or None if not found or malformed.
        """
        href_attr = callout.get("xlink:href")  # Prioritize xlink:href
        if href_attr is None:
            # Fallback to plain href if xlink:href is not present
            href_attr = callout.get("href")
        return normalize_href_attr(href_attr)

    def _process_callout(
        self,
        callout: Tag,
        href: str,
        index: int,
        notes_soup: BeautifulSoup,
    ) -> bool:
        """Processes a single callout, returning True if successful.

        Args:
            callout (Tag): The BeautifulSoup `Tag` representing the callout.
            href (str): The pre-validated href attribute of the callout.
            index (int): The sequential index of the callout.
            notes_soup (BeautifulSoup): The soup object containing the note bodies.

        Returns:
            bool: `True` if the callout was successfully processed, `False` otherwise.

        Mutations:
            - Modifies the `callout` tag's `id` attribute.
            - Calls `_ensure_backlink` to modify the `note_body`.
        """
        if not href.startswith("#"):
            # Log non-fragment hrefs as anomalies
            self.unresolved_targets.append(
                (self._UnresolvedReason.NON_FRAGMENT, href, callout),
            )
            return False

        target_id = href[1:]
        note_body = notes_soup.select_one(f"#{target_id}")

        if not note_body:
            self.unresolved_targets.append(
                (self._UnresolvedReason.DANGLING, href, callout),
            )
            return False

        return_id = f"fnref-{target_id}-{index}"
        callout["id"] = return_id
        self._ensure_backlink(
            notes_soup,
            note_body,
            return_id,
        )

        return True

    def _determine_status(self, notes_count: int) -> PipelineStatus:
        """Determines the final pipeline status based on processing results."""
        if self.unresolved_targets:
            return (
                PipelineStatus.PARTIAL_SUCCESS
                if notes_count > 0
                else PipelineStatus.ERROR
            )
        return (
            PipelineStatus.SUCCESS if notes_count > 0 else PipelineStatus.SUCCESS_NOOP
        )

    def _create_anomaly_entry(
        self,
        reason: _UnresolvedReason,
        href_val: str,
    ) -> dict[str, Any]:
        """Constructs a standardized anomaly dictionary entry for reporting.

        Args:
            reason: The reason the callout was unresolved.
            href_val: The href value that caused the anomaly.

        Returns:
            A dictionary representing the structured anomaly.
        """
        if reason == self._UnresolvedReason.NON_FRAGMENT:
            key = AnomalyKey.MALFORMED_HREF
            message = f"Callout href '{href_val}' is not a valid fragment identifier (must start with '#')."
        else:  # reason == self._UnresolvedReason.DANGLING
            key = AnomalyKey.DANGLING_REF
            message = f"Callout href '{href_val}' points to a missing note body."

        return {
            "key": key,
            "message": message,
            "payload": {
                "notes_file_key": self.notes_file_key,
                "callout_href": href_val,
            },
        }

    def process(
        self,
        soup: BeautifulSoup,
        context: BookStyleContext,
        all_soups: dict[str, BeautifulSoup] | None = None,
        current_soup_key: str | None = None,
    ) -> tuple[BeautifulSoup, dict[str, Any]]:
        """Synthesizes and injects backlinks for native note conventions.

        This method finds all forward note links, generates unique return IDs
        for them, and injects corresponding backlink anchors into the note
        bodies located in the specified donor file.

        Args:
            soup (BeautifulSoup): The DOM tree containing the note callouts.
            context (BookStyleContext): The shared context for the book.
            all_soups (dict[str, BeautifulSoup] | None): A dictionary mapping all
                file keys to their soup objects, used to find cross-file notes.

        Returns:
            tuple[BeautifulSoup, dict[str, Any]]: A tuple containing the mutated
                soup and a metadata dictionary.

        Raises:
            Exception: Per Global Directive #1, any unexpected native exceptions
                will be caught, logged as CRITICAL, and re-raised.

        Mutations:
            - Injects a backlink `<a>` tag with `role="doc-backlink"` into the
              note body node found in the donor file.

        Rules & Limits:
            - Callout Selector: Finds all `<a type="note" xlink:href="#target_id">`.
            - Return ID Synthesis: A unique return ID is generated for each callout
              with the format `fnref-{target_id}-{sequential_index}`.
            - Backlink Injection: A new backlink anchor is injected into the corresponding
              note body, which may reside in a different document.
            - Broken Link Handling: If a `target_id` does not resolve to a node,
              the `href` is added to `self.unresolved_targets`
              for telemetry, and the pair is skipped. The process does not abort.
            - Full depth traversal: Yes.

        Calls:
            - `_process_callout`: For each callout to handle individual processing.
            - `_ensure_backlink` (inherited): To create backlinks in note bodies.
            - `_determine_status`: To set the final pipeline status.
            - `get_utc_timestamp`: To record the execution time.
        """
        self.unresolved_targets = []
        start_time = get_utc_timestamp()

        if self.notes_file_key and all_soups and self.notes_file_key in all_soups:
            notes_soup = all_soups[self.notes_file_key]
        else:
            notes_soup = soup
            if self.notes_file_key:
                log.warning(
                    "Note file key '%s' not found. Searching for notes in the current document.",
                    self.notes_file_key,
                )

        notes_count = sum(
            bool(self._process_callout(callout, href, i, notes_soup))
            for i, (callout, href) in enumerate(self._iter_note_callouts(soup), 1)
        )
        status = self._determine_status(notes_count)

        anomalies_payload = [
            self._create_anomaly_entry(reason, href_val)
            for reason, href_val, _ in self.unresolved_targets
        ]

        notes_found_count = notes_count
        notes_rebuilt_count = (
            0  # This strategy does not rebuild notes into a new section
        )
        backlinks_injected_count = notes_count
        anomalies_repaired_count = len(anomalies_payload)
        return soup, BaseFootnoteStrategy.create_metadata(
            strategy_name="NativeConventionFootnoteStrategy",
            status=status,
            notes_processed_count=backlinks_injected_count,
            notes_found_count=notes_found_count,
            notes_rebuilt_count=notes_rebuilt_count,
            backlinks_injected_count=backlinks_injected_count,
            anomalies=anomalies_payload,
            anomalies_repaired_count=anomalies_repaired_count,
            start_time=start_time,
        )
