"""A data-driven strategy for publisher-specific footnote patterns.

This module provides the `ParameterizedFootnoteStrategy`, a flexible (Stage B)
strategy that processes footnotes based on declarative patterns loaded from a
configuration registry. It is designed to handle footnote structures that follow
a consistent but non-standard pattern, allowing the system to adapt to new
publisher styles without code changes.

Analytical Blueprint:
---------------------
- **Objective:** To identify and normalize footnote structures by applying a set
  of pre-configured CSS selectors for callouts, bodies, and backlinks.
- **Components:**
  - `ParameterizedFootnoteStrategy`: The main class, initialized with a
    dictionary of configuration parameters (`config_params`).
  - `can_process`: Checks if any elements matching the configured `body_selector`
    exist in the DOM.
  - `process`: Orchestrates the normalization using the configured selectors and
    the common helpers from `BaseFootnoteStrategy`.
  - `_get_soups_to_search`: Determines which document(s) to search for note
    bodies based on the `body_topology_location` configuration.
  - `_aggregate_note_bodies`: Collects all note bodies from the specified
    documents.
- **Analytical Steps:**
  1. At initialization, load the `callout_selector`, `body_selector`,
     `backlink_selector`, and `body_topology_location` from the provided
     `config_params`.
  2. Determine the search scope for note bodies (current document vs. all
     documents in the book).
  3. Extract all note bodies from the search scope using `body_selector`.
  4. Find all callouts in the current document using `callout_selector`.
  5. Match callouts to bodies based on their `href` and `id` attributes.
- **Transformation Rules:**
  - Matched callouts and bodies are standardized using the helpers from
    `BaseFootnoteStrategy`.
  - Callouts are converted to a canonical `<a role="doc-noteref">` format.
  - Note bodies are converted to canonical `<li>` elements.
  - Backlinks are found using `backlink_selector` or synthesized if missing.
  - All processed notes are rebuilt into a single, standardized `<section>`.
- **Output:**
  - A mutated `BeautifulSoup` object with a standardized footnote section.
  - A metadata dictionary where the strategy name is dynamically set to
    `ParameterizedFootnoteStrategy:<pattern_id>`.
"""

import logging
import re
from dataclasses import dataclass
from typing import Any

from bs4 import BeautifulSoup, Tag

from dom_normalizer.core import BookStyleContext, PipelineStatus
from dom_normalizer.core.dom_utils import clone_tag, get_utc_timestamp

from .base_strategy import (
    AnomalyKey,
    BaseFootnoteStrategy,
    FootnoteStrategyError,
    _Anomaly,
    _AnomalyCollector,
)

log = logging.getLogger(__name__)


class _ConfigurationError(FootnoteStrategyError):
    """Configuration-related error used to distinguish from runtime ValueError."""


@dataclass(frozen=True)
class _ForensicSignatureConfig:
    """Validated configuration for the forensic_signature part of the pattern."""

    callout_selector: str
    body_selector: str
    backlink_selector: str
    topology_location: str
    fail_on_donor_file_missing: bool


@dataclass(frozen=True)
class _PatternConfig:
    """An immutable container for validated strategy configuration."""

    pattern_id: str
    signature: _ForensicSignatureConfig
    detection_classes: frozenset[str]


class ParameterizedFootnoteStrategy(BaseFootnoteStrategy):
    """
    A data-driven strategy (Stage B) that processes footnotes based on
    declarative patterns loaded from a configuration registry.

    This strategy is designed to handle footnote structures that do not conform
    to standard semantic markup (like DPUB-ARIA) but follow a consistent,
    discoverable pattern within a specific book or publisher's style. Instead of
    hard-coding logic, it uses CSS selectors and other parameters provided at
    initialization to identify and process footnote callouts and bodies.

    This approach allows the system to be extended to support new, unknown
    footnote styles simply by adding a new pattern configuration to the registry,
    without requiring any changes to the Python code.
    """

    ALLOWED_TOPOLOGY_LOCATIONS: frozenset[str] = frozenset(
        {"donor_file", "end_of_section"},
    )

    def __init__(self, config_params: dict[str, Any]) -> None:
        """Initializes a unified strategy guided by declarative metadata.

        This strategy maps persisted forensic variables from a configuration
        dictionary to deterministic BeautifulSoup transformations, eliminating
        the need for probabilistic runtime code generation.

        Args:
            config_params (dict[str, Any]): A dictionary containing the pattern
                configuration, including a `forensic_signature` sub-dictionary.

        Returns:
            None

        Raises:
            KeyError: If `forensic_signature` or its required keys are missing.

        Mutations:
            - Sets instance variables from `config_params['forensic_signature']`:
              `self.callout_selector`, `self.body_selector`, `self.topology_location`.
            - Sets `self.backlink_selector` with a fallback to `'a'`.

        Rules & Limits:
            - Instance Lifecycle: Assumes this instance is scoped to a single book.
        """
        super().__init__()
        self.config = config_params
        self.config_data = self._load_and_validate_config(
            config_params,
        )
        self.detection_classes = self.config_data.detection_classes
        self.callout_selector = self.config_data.signature.callout_selector
        self.body_selector = self.config_data.signature.body_selector
        self.backlink_selector = self.config_data.signature.backlink_selector
        self.topology_location = self.config_data.signature.topology_location
        self.fail_on_donor_file_missing = (
            self.config_data.signature.fail_on_donor_file_missing
        )

    def _load_and_validate_signature(
        self,
        signature_data: dict[str, Any],
        pattern_id: str,
    ) -> _ForensicSignatureConfig:
        """Loads and validates the forensic_signature part of the configuration."""
        required_keys = {
            "callout_selector",
            "body_selector",
            "body_topology_location",
        }
        if missing_keys := required_keys - set(signature_data):
            raise _ConfigurationError(
                f"Parameterized strategy '{pattern_id}' is missing required "
                f"forensic_signature keys: {sorted(missing_keys)}",
            )

        for key in ["callout_selector", "body_selector"]:
            if (
                not isinstance(signature_data.get(key), str)
                or not signature_data[key].strip()
            ):
                raise _ConfigurationError(
                    f"`{key}` in forensic_signature must be a non-empty string.",
                )

        backlink_selector = signature_data.get("backlink_selector", "a")
        if not isinstance(backlink_selector, str) or not backlink_selector.strip():
            raise _ConfigurationError(
                "`backlink_selector` in forensic_signature must be a non-empty string.",
            )

        topology_location = signature_data["body_topology_location"]
        if topology_location not in self.ALLOWED_TOPOLOGY_LOCATIONS:
            raise _ConfigurationError(
                f"Invalid body_topology_location={topology_location!r}. "
                f"Allowed values: {sorted(self.ALLOWED_TOPOLOGY_LOCATIONS)}",
            )

        callout_selector = signature_data["callout_selector"]
        if "[" in callout_selector or ":" in callout_selector:
            log.warning(
                "Pattern '%s' uses a complex callout_selector ('%s'). "
                "The regex-based class parser may not extract all detection classes. "
                "This is safe if detection relies on attributes/pseudo-classes, "
                "but may affect class-based detection.",
                pattern_id,
                callout_selector,
            )

        return _ForensicSignatureConfig(
            callout_selector=callout_selector,
            body_selector=signature_data["body_selector"],
            backlink_selector=backlink_selector,
            topology_location=topology_location,
            fail_on_donor_file_missing=signature_data.get(
                "fail_on_donor_file_missing",
                False,
            ),
        )

    def _load_and_validate_config(
        self,
        config_params: dict[str, Any],
    ) -> "_PatternConfig":
        """Loads and validates the strategy configuration, returning a structured object."""
        pattern_id = config_params.get("pattern_id")
        if not isinstance(pattern_id, str) or not pattern_id.strip():
            raise _ConfigurationError("`pattern_id` must be a non-empty string.")

        signature_data = config_params.get("forensic_signature")
        if not isinstance(signature_data, dict):
            raise _ConfigurationError("`forensic_signature` must be a dictionary.")

        signature_config = self._load_and_validate_signature(signature_data, pattern_id)

        detection_classes = self._parse_detection_classes_from_selector(
            signature_config.callout_selector,
        )
        if not detection_classes:
            log.debug(
                "No detection classes found in callout_selector '%s' for pattern '%s'. "
                "This is normal if detection relies on attributes instead of classes.",
                signature_config.callout_selector,
                pattern_id,
            )

        return _PatternConfig(
            pattern_id=pattern_id,
            signature=signature_config,
            detection_classes=detection_classes,
        )

    @staticmethod
    def _parse_detection_classes_from_selector(selector: str) -> frozenset[str]:
        """Extracts class names from a CSS selector string.

        This is a simple utility to find class names (e.g., `.foo`) in a
        selector. It is not a full CSS parser and has limitations, but it is
        sufficient for extracting the detection classes used by this strategy.
        It does not handle attribute selectors (e.g., `[class~=foo]`) or
        pseudo-classes.

        This helper intentionally collects **all** occurrences of `.class`
        across the full selector string, including descendant and compound
        selectors (for example, ``div.note .callout`` produces
        ``{"note", "callout"}``). Callers should ensure that the selector does
        not include unrelated classes; the returned set is used for detection
        rather than to model only the classes on the final target element.

        Args:
            selector: The CSS selector string.

        Returns:
            A frozenset of class names found in the selector.
        """
        # Find all occurrences of .class-name in the selector.
        return frozenset(re.findall(r"\.([\w-]+)", selector))

    def can_process(self, soup: BeautifulSoup, context: BookStyleContext) -> bool:
        """Evaluates if the parameterized structural selectors exist in the DOM.

        Args:
            soup (BeautifulSoup): The DOM tree to evaluate.
            context (BookStyleContext): The shared context for the book (unused).

        Returns:
            bool: `True` if `soup.select(self.body_selector)` finds at least one
                element, `False` otherwise.

        Raises:
            Exception: Per Global Directive #1, any unexpected native exceptions
                will be caught, logged as CRITICAL, and re-raised.

        Mutations:
            None.

        Rules & Limits:
            - Full depth traversal: Yes.
        """
        try:
            bodies = soup.select(self.body_selector)
            # Check for bodies without IDs even if the list is not empty.
            # This warning is useful for debugging configurations.
            if any(not body.get("id") for body in bodies):
                log.warning(
                    "ParameterizedStrategy: body_selector '%s' matched elements without an 'id' attribute. "
                    "These will be ignored during processing.",
                    self.body_selector,
                )
            return bool(bodies)
        except Exception:
            log.critical(
                "Unexpected error in ParameterizedFootnoteStrategy.can_process for pattern %s",
                self.config_data.pattern_id,
                exc_info=True,
            )
            raise

    def _get_soups_to_search(
        self,
        current_soup: BeautifulSoup,
        all_soups: dict[str, BeautifulSoup] | None,
        collector: "_AnomalyCollector",
        current_soup_key: str,
    ) -> dict[str, BeautifulSoup]:
        """Determines which documents to search for note bodies based on topology."""
        if self.topology_location == "end_of_section":
            return {current_soup_key: current_soup}

        # This handles the 'donor_file' case.
        if all_soups:
            return all_soups

        message = "Topology is 'donor_file' but no other documents were provided."
        if self.fail_on_donor_file_missing:
            raise _ConfigurationError(f"{message} Configuration requires failing fast.")

        collector.add(
            key=AnomalyKey.CONFIG_ERROR,
            message=f"{message} Falling back to current document.",
        )
        return {"current_document": current_soup}

    def _aggregate_note_bodies(
        self,
        soups_to_search: dict[str, BeautifulSoup],
        collector: "_AnomalyCollector",
        current_soup: BeautifulSoup,
    ) -> dict[str, Tag]:
        """Extracts note bodies from multiple soups, handling duplicates.

        It iterates through a list of soup objects, extracts note bodies using
        the provided selector, and aggregates them into a single dictionary.
        If duplicate note IDs are found, it keeps the first one encountered and
        records an anomaly.

        Args:
            soups_to_search: A dictionary of BeautifulSoup objects to search, keyed by source label.
            collector: The collector for anomalies.
            current_soup: The soup object for the document currently being processed.

        Returns:
            A dictionary of note body tags keyed by their ID.
        """
        note_bodies: dict[str, Tag] = {}
        note_body_sources: dict[str, str] = {}

        for source_label, s in soups_to_search.items():
            # Inlined and modified from BaseFootnoteStrategy._extract_note_bodies
            # to handle cloning from donor documents.
            for body in s.select(self.body_selector):
                if not body.get("id"):
                    continue

                note_id = str(body["id"])
                if s is current_soup:
                    body_tag = body.extract()
                else:
                    # Clone the tag to avoid direct mutation of a tag from a donor soup
                    # in later steps, then remove the original to consolidate notes.
                    body_tag = clone_tag(body)
                    body.decompose()

                if note_id not in note_bodies:
                    note_bodies[note_id] = body_tag
                    note_body_sources[note_id] = source_label
                else:
                    first_source_label = note_body_sources.get(note_id)
                    collector.add(
                        key=AnomalyKey.DUPLICATE_ID,
                        message=(
                            f"Note body '#{note_id}' found in {source_label} already exists. "
                            f"First occurrence was in {first_source_label}. "
                            "Keeping first instance."
                        ),
                        source=source_label,
                        payload={
                            "note_id": note_id,
                            "first_source": first_source_label,
                            "duplicate_source": source_label,
                        },
                    )
        return note_bodies

    def _determine_status(
        self,
        notes_processed_count: int,
        anomalies: list[_Anomaly],
    ) -> PipelineStatus:
        """Determines the final pipeline status based on processing results.

        Args:
            notes_processed_count: The number of successfully processed notes.
            anomalies: A list of structured anomaly objects.

        Returns:
            The final PipelineStatus for the process.
        """
        if anomalies:
            return (
                PipelineStatus.PARTIAL_SUCCESS
                if notes_processed_count > 0
                else PipelineStatus.ERROR
            )
        return (
            PipelineStatus.SUCCESS
            if notes_processed_count > 0
            else PipelineStatus.SUCCESS_NOOP
        )

    def _create_metadata(
        self,
        status: PipelineStatus,
        notes_processed_count: int,
        notes_found_count: int,
        notes_rebuilt_count: int,
        backlinks_injected_count: int,
        collector: "_AnomalyCollector",
        start_time: str,
    ) -> dict[str, Any]:
        """Constructs the standardized metadata payload for this strategy."""
        return BaseFootnoteStrategy.create_metadata(
            strategy_name=f"ParameterizedFootnoteStrategy:{self.config_data.pattern_id}",
            status=status,
            notes_processed_count=notes_processed_count,
            notes_found_count=notes_found_count,
            notes_rebuilt_count=notes_rebuilt_count,
            backlinks_injected_count=backlinks_injected_count,
            anomalies=collector.to_list(),
            anomalies_repaired_count=len(collector.anomalies),
            start_time=start_time,
        )

    def _collect_post_processing_anomalies(
        self,
        collector: "_AnomalyCollector",
        notes_count: int,
        note_bodies: dict[str, Tag],
        used_ids: set[str],
        callouts: list[Tag],
    ) -> None:
        """Collects anomalies that can only be detected after processing callouts.

        This helper centralizes the logic for identifying and reporting anomalies
        that require the full context of a processing run, such as orphan notes
        and potential configuration errors.

        Args:
            collector: The collector for anomalies.
            notes_count: The number of successfully processed notes.
            note_bodies: A dictionary of all found note bodies.
            used_ids: A set of note body IDs that were successfully referenced.
            callouts: A list of all callout tags found in the document.
        """
        # Handle orphans by finding which bodies were not used.
        orphan_ids = set(note_bodies.keys()) - used_ids
        for orphan_id in orphan_ids:
            collector.add(
                key=AnomalyKey.ORPHAN_NOTE,
                message=f"Note body '#{orphan_id}' was found but not referenced.",
            )

        # Detect a likely configuration error. This is flagged only when:
        # 1. Callouts were found.
        # 2. Note bodies were found.
        # 3. No notes were successfully processed.
        # 4. No malformed hrefs were detected (which would explain the failure).
        # This combination strongly suggests that the callout hrefs do not match
        # the note body IDs, pointing to a selector mismatch.
        has_malformed_href = any(
            anomaly.key == AnomalyKey.MALFORMED_HREF for anomaly in collector.anomalies
        )
        if notes_count == 0 and note_bodies and callouts and not has_malformed_href:
            collector.add(
                key=AnomalyKey.CONFIG_ERROR,
                message="Callouts and bodies were found, but no notes were processed. "
                "This suggests a mismatch between callout hrefs and body IDs.",
            )

    def _run_processing_workflow(
        self,
        soup: BeautifulSoup,
        all_soups: dict[str, BeautifulSoup] | None,
        current_soup_key: str | None,
    ) -> tuple[BeautifulSoup, dict[str, Any]]:
        """Orchestrates the main processing logic and returns final metadata.

        This helper method encapsulates the core workflow of the strategy:
        initializing the anomaly collector, finding note bodies, processing
        callouts, collecting post-processing anomalies, rebuilding the notes
        section, and generating the final metadata payload.

        Args:
            soup: The DOM tree to mutate.
            all_soups: A dictionary of all soup objects in the book.
            current_soup_key: The key for the current `soup` in `all_soups`.

        Returns:
            A tuple containing the mutated soup and a metadata dictionary.
        """
        collector = _AnomalyCollector()
        start_time = get_utc_timestamp()

        final_current_soup_key = current_soup_key
        if not final_current_soup_key:
            if all_soups:
                # Fallback to identity check if key is not provided, with a warning.
                for key, s_obj in all_soups.items():
                    if s_obj is soup:
                        final_current_soup_key = key
                        break
            if final_current_soup_key:
                log.warning(
                    "Current soup key not provided for pattern '%s'; falling back to "
                    "fragile identity check. The caller should be updated to pass "
                    "'current_soup_key' to the process method.",
                    self.config_data.pattern_id,
                )
            else:
                # If still not found, or if all_soups is None.
                final_current_soup_key = "current_document"

        soups_to_search = self._get_soups_to_search(
            soup,
            all_soups,
            collector,
            final_current_soup_key,
        )
        note_bodies = self._aggregate_note_bodies(soups_to_search, collector, soup)
        processed_notes, notes_count, used_ids = self._process_callouts(
            soup,
            note_bodies,
            collector,
        )

        callouts = soup.select(self.callout_selector)
        self._collect_post_processing_anomalies(
            collector,
            notes_count,
            note_bodies,
            used_ids,
            callouts,
        )

        self._rebuild_notes_section(soup, processed_notes)

        status = self._determine_status(
            notes_count,
            collector.anomalies,
        )  # notes_count here is notes_processed_count
        metadata = self._create_metadata(
            status,
            notes_count,
            len(note_bodies),
            len(processed_notes),
            notes_count,
            collector,
            start_time,
        )
        return soup, metadata

    def process(
        self,
        soup: BeautifulSoup,
        context: BookStyleContext,
        all_soups: dict[str, BeautifulSoup] | None = None,
        current_soup_key: str | None = None,
    ) -> tuple[BeautifulSoup, dict[str, Any]]:
        """Executes in-place mutations by applying the configured selectors.

        Args:
            soup (BeautifulSoup): The DOM tree to mutate.
            context (BookStyleContext): The shared context for the book.
            all_soups: A dictionary of all soup objects in the book.
            current_soup_key: The key for the current `soup` in `all_soups`.

        Returns:
            tuple[BeautifulSoup, dict[str, Any]]: A tuple containing the mutated
                soup and a metadata dictionary conforming to the YAML contract.

        Raises:
            Exception: Per Global Directive #1, any unexpected native exceptions
                will be caught, logged as CRITICAL, and re-raised.

        Mutations:
            - The input `soup` object is modified in-place based on the logic
              defined by the instance's configured selectors.
        Rules & Limits:
            - Full depth traversal: Yes.

        Calls:
            - `_extract_note_bodies` (inherited): To get all note bodies.
            - `_process_callouts` (inherited): To match callouts with bodies and standardize them.
            - `_rebuild_notes_section` (inherited): To create a new, standardized footnote section.
            - `get_utc_timestamp`: To record the execution time.
        """
        # pylint: disable=unused-argument
        try:
            return self._run_processing_workflow(soup, all_soups, current_soup_key)
        except _ConfigurationError as e:
            # Configuration-related errors (e.g., fail_on_donor_file_missing)
            # are logged as errors but not critical failures.
            log.exception(
                "Configuration error in ParameterizedFootnoteStrategy.process for pattern %s: %s",
                self.config_data.pattern_id,
                e,
            )
            raise
        except Exception:  # Other unexpected runtime errors
            log.critical(
                "Unexpected error in ParameterizedFootnoteStrategy.process for pattern %s",
                self.config_data.pattern_id,
                exc_info=True,
            )
            raise
