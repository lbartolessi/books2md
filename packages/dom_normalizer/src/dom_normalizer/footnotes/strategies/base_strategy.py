"""Defines the abstract base class and common utilities for all footnote strategies.

This module provides the `BaseFootnoteStrategy`, an abstract base class that
enforces a consistent interface for all footnote processing strategies within the
pipeline. It also includes a suite of shared, reusable helper methods for common
DOM manipulation tasks, such as extracting note bodies, standardizing callouts,
ensuring backlinks, and rebuilding a canonical notes section.

By inheriting from this class, concrete strategies can focus on their specific
detection logic (`can_process`) while leveraging a robust, centralized toolkit
for the actual DOM mutation (`process`).

Analytical Blueprint:
---------------------
- **Objective:** To define a standard contract for all footnote strategies and
  provide a centralized toolkit of high-level, reusable helper methods for
  footnote normalization.
- **Components:**
  - `BaseFootnoteStrategy(ABC)`: The abstract base class defining the common
    interface.
  - `can_process(abstractmethod)`: Abstract method contract for determining if a
    strategy is applicable to a given DOM.
  - `process(abstractmethod)`: Abstract method contract for executing the
    strategy's normalization logic.
  - `_extract_note_bodies`: Helper to find and extract note body elements.
  - `_process_callouts`: Helper to iterate through callouts, match them to
    bodies, and standardize both.
  - `_standardize_callout`: Helper to canonicalize a callout `<a>` tag.
  - `_standardize_note_body`: Helper to convert a note body into a canonical `<li>`.
  - `_ensure_backlink`: Helper to find or synthesize a backlink in a note body.
  - `_rebuild_notes_section`: Helper to construct the final, standardized
    `<section role="doc-endnotes">`.
- **Analytical Steps (for subclasses):**
  1. Use `can_process` to check for applicability.
  2. In `process`, use `_extract_note_bodies` to collect all potential note bodies.
  3. Use `_process_callouts` to iterate through callouts, match them to the
     extracted bodies, and apply standardization helpers.
  4. Collect any unreferenced bodies as "orphan" anomalies.
  5. Use `_rebuild_notes_section` to append the standardized notes to the document.
- **Output:**
  - Concrete strategies must return a tuple: `(BeautifulSoup, dict[str, Any])`,
    containing the mutated soup and a metadata dictionary.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Final

from bs4 import BeautifulSoup, NavigableString, Tag

from dom_normalizer.core.dom_utils import (
    coerce_class_list,
    get_tag_identifier,
    get_utc_timestamp,
)

from ...core import BookStyleContext, PipelineStatus

if TYPE_CHECKING:
    from ..footnote_processor import FootnoteProcessor


class FootnoteStrategyError(Exception):
    """Base class for errors specific to footnote strategies."""


STRATEGY_PROCESSOR_UNBOUND_MSG: Final[str] = (
    "Strategy has not been bound to a processor instance."
)

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Anomaly:
    """Represents a structured anomaly for reporting."""

    key: str
    message: str
    source: str | None = None
    payload: dict[str, Any] | None = None

class AnomalyCollector:
    """A helper to collect and manage structured anomalies."""

    def __init__(self) -> None:
        self.anomalies: list[Anomaly] = []

    def add(
        self,
        key: str,
        message: str,
        source: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """Adds a new anomaly.""" # Anomaly is now public, so no need for _Anomaly
        self.anomalies.append(
            Anomaly(key=key, message=message, source=source, payload=payload),
        )

    def to_list(self) -> list[dict[str, Any]]:
        """Converts the collected anomalies to a list of dictionaries."""
        return [asdict(anomaly) for anomaly in self.anomalies]


class AnomalyKey(StrEnum):
    """Defines standardized keys for anomaly reporting."""

    CONFIG_ERROR = "configuration-error"
    DANGLING_REF = "dangling-ref"
    DUPLICATE_ID = "duplicate-id"
    CRITICAL_ERROR = "critical-error"
    MALFORMED_HREF = "malformed-href"
    ORPHAN_NOTE = "orphan-note"


def normalize_href_attr(href_attr: Any) -> str | None:
    """Normalize a raw href attribute value to a usable string or None.

    Returns:
        str | None: A single usable href string, or None if the value is
        non-usable (empty, invalid list, unexpected type, etc.).

    BeautifulSoup can sometimes return a list of strings; this is anomalous for
    href attributes. We log anomalous multi-valued hrefs but only return a
    single usable value when it can be determined unambiguously.

    Callers only need to:
      * check `normalized is None` to skip non-usable hrefs, and
      * apply structural checks like `normalized.startswith("#")` as needed.
    """
    if isinstance(href_attr, str):
        stripped = href_attr.strip()
        return stripped or None

    if isinstance(href_attr, list):
        # Filter for usable string values in the list.
        usable_values = [
            value for value in href_attr if isinstance(value, str) and value.strip()
        ]

        if len(usable_values) == 1:
            return usable_values[0]

        if len(usable_values) > 1:
            log.warning(
                "FootnoteProcessor: ambiguous multi-valued href attribute encountered; "
                "values=%r. Skipping due to ambiguity.",
                href_attr,
            )
        # Return None for empty lists, lists with no usable values, or ambiguous lists.
        return None

    # Handles `None` and any other unexpected types.
    if href_attr is not None:
        log.warning(
            "FootnoteProcessor: unexpected href attribute type %r; value=%r. "
            "This is an invalid href.",
            type(href_attr),
            href_attr,
        )
    return None


class BaseFootnoteStrategy(ABC):
    """Abstract base class for all footnote processing strategies.

    implement. It enforces the presence of `can_process` and `process` methods,
    ensuring a consistent API for the `FootnoteProcessor`. It also provides a
    suite of common helper methods for DOM manipulation, which can be inherited
    and used by concrete strategy implementations.
    """

    def __init__(self) -> None:
        """Initializes the base strategy with common attributes."""
        self.detection_classes: frozenset[str] = frozenset()
        self.callout_selector: str = ""
        self.body_selector: str = ""
        self.backlink_selector: str = ""
        self.processor: FootnoteProcessor | None = None

    @abstractmethod
    def can_process(self, soup: BeautifulSoup, context: BookStyleContext) -> bool:
        """Evaluates if the DOM resource contains elements matching the strategy.

        Args:
            soup (BeautifulSoup): The DOM tree to evaluate.
            context (BookStyleContext): The shared context for the book.

        Returns:
            bool: `True` if the strategy can process the document, `False` otherwise.

        Raises:
            Exception: Per Global Directive #1, any unexpected native exceptions
                during processing will be caught, logged as CRITICAL, and re-raised.

        Mutations:
            None.

        Rules & Limits:
            - Full depth traversal: Yes.
        """
        raise NotImplementedError

    @abstractmethod
    def process(
        self,
        soup: BeautifulSoup,
        context: BookStyleContext,
        all_soups: dict[str, BeautifulSoup] | None = None,
        current_soup_key: str | None = None,
    ) -> tuple[BeautifulSoup, dict[str, Any]]:
        """Executes the in-place mutation and returns the result.

        Args:
            soup (BeautifulSoup): The DOM tree to mutate.
            context (BookStyleContext): The shared context for the book.
            all_soups (dict[str, BeautifulSoup] | None): A dictionary mapping all
                file keys in the book to their soup objects. Defaults to None.
            current_soup_key (str | None): The key for the current `soup` object
                within `all_soups`. Defaults to None.

        Returns:
            tuple[BeautifulSoup, dict[str, Any]]: A tuple containing the mutated
                soup object and a dictionary with metadata about the process,
                conforming to the YAML contract.

        Raises:
            Exception: Per Global Directive #1, any unexpected native exceptions
                during processing will be caught, logged as CRITICAL, and re-raised.

        Mutations:
            - The input `soup` object is expected to be modified in-place.

        Rules & Limits:
            - Full depth traversal: Yes.
        """
        raise NotImplementedError

    # --- Common Helper Methods for Subclasses ---

    @staticmethod
    def create_metadata(
        strategy_name: str,
        status: PipelineStatus,
        notes_processed_count: int,
        notes_found_count: int = 0,
        notes_rebuilt_count: int = 0,
        backlinks_injected_count: int = 0,
        anomalies: list[dict[str, Any]] | None = None,
        anomalies_repaired_count: int = 0,
        start_time: str | None = None,
    ) -> dict[str, Any]:
        """Constructs a standardized metadata dictionary for a footnote strategy.

        Args:
            strategy_name: The name of the strategy that was applied.
            status: The final status of the processing.
            notes_processed_count: The number of notes successfully processed (matched and standardized).
            notes_found_count: The total number of note bodies initially found by the strategy.
            notes_rebuilt_count: The number of note bodies that were moved/recreated in the canonical section.
            backlinks_injected_count: The number of backlinks that were added or ensured.
            anomalies: A list of any anomalies detected during processing.
            start_time: The ISO 8601 UTC timestamp for when processing began.

        Returns:
            A dictionary conforming to the standard metadata contract.
        """
        if anomalies is None:
            anomalies = []
        if start_time is None:
            start_time = get_utc_timestamp()

        payload = {
            "strategy_applied": strategy_name,
            "processing_status": status.value,
            "notes_processed_count": notes_processed_count,
            "notes_found_count": notes_found_count,
            "notes_rebuilt_count": notes_rebuilt_count,
            "backlinks_injected_count": backlinks_injected_count,
            "anomalies_detected": anomalies,
            "anomalies_repaired_count": anomalies_repaired_count,
            "execution_timestamp": start_time,
        }
        return {"footnote_processing": payload}

    def _add_malformed_href_anomaly(
        self,
        collector: AnomalyCollector,
        callout: Tag,
        raw_href: Any,
        message: str,
        normalized_href: str | None = None,
    ) -> None:
        """Adds a structured anomaly for a malformed href.

        Args:
            collector: The anomaly collector instance.
            callout: The callout tag with the malformed href.
            raw_href: The original, un-normalized href attribute value.
            message: The specific error message for the anomaly.
            normalized_href: The normalized href, if available.
        """
        payload = {
            "raw_href": str(raw_href),
            "callout_identifier": get_tag_identifier(
                callout,
                attr_value_limit=100,
            ),
        }
        if normalized_href is not None:
            payload["normalized_href"] = normalized_href
        collector.add(
            key=AnomalyKey.MALFORMED_HREF,
            message=message,
            payload=payload,
        )

    def _add_dangling_ref_anomaly(
        self,
        collector: AnomalyCollector,
        callout: Tag,
        target_id: str,
    ) -> None:
        """Adds a structured anomaly for a dangling reference.

        Args:
            collector: The anomaly collector instance.
            callout: The callout tag with the dangling reference.
            target_id: The ID of the note body that was not found.
        """
        collector.add(
            key=AnomalyKey.DANGLING_REF,
            message=f"Callout points to missing note body '#{target_id}'.",
            payload={
                "callout_identifier": get_tag_identifier(
                    callout,
                    attr_value_limit=100,
                ),
            },
        )

    def _extract_note_bodies(
        self,
        soup: BeautifulSoup,
    ) -> dict[str, Tag]:
        """Finds and extracts note bodies using a given selector, keyed by ID.

        This method scans the DOM for elements explicitly marked as footnote
        bodies using a provided CSS selector. Found bodies are extracted
        from their original position in the DOM and stored in a dictionary
        for later processing. It uses a dictionary comprehension for conciseness
        and efficiency.

        Args:
            soup (BeautifulSoup): The DOM tree to search within.

        Returns:
            dict[str, Tag]: A dictionary where keys are the `id` attributes
                of the note bodies and values are the BeautifulSoup `Tag` objects
                representing those bodies.

        Raises:
            None

        Mutations:
            - Extracts (removes) the identified note body `Tag` objects from
              the `soup` object.

        Rules & Limits:
            - ID Requirement: Only elements with a valid `id` attribute are collected.
        """
        if not self.body_selector:
            log.warning(
                "Strategy %s has an empty body_selector; cannot extract note bodies.",
                self.__class__.__name__,
            )
            return {}
        return {
            str(body["id"]): body.extract()
            for body in soup.select(self.body_selector)
            if body.get("id")
        }

    def _standardize_callout(
        self,
        callout: Tag,
        index: int,
    ) -> str:
        """Standardizes a callout tag in-place and returns its new ID.

        This method ensures that a footnote callout (`<a>` tag) conforms to
        a canonical structure, including `id`, `href`, `role`, and `epub:type`
        attributes.

        Args:
            callout (Tag): The BeautifulSoup `Tag` representing the callout.
            index (int): The sequential index of the callout, used for ID generation.

        Returns:
            str: The newly assigned canonical ID for the callout.
        """
        callout_id = f"fnref-{index}"
        callout["id"] = callout_id
        callout["href"] = f"#fn-{index}"
        callout["role"] = "doc-noteref"
        # Remove non-canonical attributes after processing.
        if "epub:type" in callout.attrs:
            del callout["epub:type"]

        # Normalize classes: remove detection-specific classes while preserving others.
        if "class" in callout.attrs:
            existing_classes = coerce_class_list(callout.get("class"))
            if normalized_classes := [  # Use self.detection_classes
                cls for cls in existing_classes if cls not in self.detection_classes
            ]:
                callout["class"] = " ".join(normalized_classes)
            else:
                del callout["class"]
        return callout_id

    def _ensure_backlink(
        self,
        soup: BeautifulSoup,
        note_body_tag: Tag,
        callout_id: str,
    ) -> None:
        """Finds or creates a backlink in the note body using a provided selector.

        This method ensures that each note body has a backlink (`<a>` tag with
        `role="doc-backlink"`) pointing back to its corresponding callout. If
        a backlink is not found, a new one is created and inserted.

        Args:
            soup (BeautifulSoup): The root BeautifulSoup object, used to create new tags.
            note_body_tag (Tag): The BeautifulSoup `Tag` representing the note body.
            callout_id (str): The ID of the callout to which the backlink should point.

        Returns:
            None

        Raises:
            None

        Mutations:
            - If no backlink is found, a new `<a>` tag is created and inserted
              into the `note_body_tag`.
            - Sets the `href`, `string`, and `class` attributes of the backlink.

        Rules & Limits:
            - Insertion Point: Attempts to insert the new backlink at the beginning
              of the first `<p>` child of the note body. If no `<p>` is found, it
              inserts at the beginning of the note body itself.
        """
        if not self.backlink_selector:
            log.warning(
                "Strategy %s has an empty backlink_selector; cannot ensure backlinks.",
                self.__class__.__name__,
            )
            return

        backlink = note_body_tag.select_one(self.backlink_selector)
        if not backlink:
            backlink = soup.new_tag("a", role="doc-backlink")
            insertion_parent = note_body_tag.select_one("p") or note_body_tag

            # Add a space before the backlink unless the parent's last content
            # is already a string ending with whitespace.
            if not (
                insertion_parent.contents
                and isinstance(insertion_parent.contents[-1], NavigableString)
                and insertion_parent.contents[-1].endswith(" ")
            ):
                insertion_parent.append(" ")
            insertion_parent.append(backlink)

        backlink["href"] = f"#{callout_id}"
        # Only add the fallback glyph if the backlink is truly empty of both
        # text content and nested tags (e.g., icons), to avoid overwriting
        # human-authored labels.
        if not backlink.get_text(strip=True) and not backlink.find_all(recursive=False):
            backlink.string = "↩"

        classes = coerce_class_list(backlink.get("class", None))

        # Normalize classes: remove detection-specific classes.
        normalized_classes = [
            cls for cls in classes if cls not in self.detection_classes
        ]  # Use self.detection_classes

        # Ensure the canonical backref class is present.
        if "footnote-backref" not in normalized_classes:
            normalized_classes.append("footnote-backref")

        # Set or remove the class attribute to avoid empty `class=""`.
        if normalized_classes:
            backlink["class"] = " ".join(normalized_classes)
        elif "class" in backlink.attrs:
            del backlink["class"]

    def _standardize_note_body(
        self,
        soup: BeautifulSoup,
        note_body_tag: Tag,
        index: int,
        callout_id: str,
    ) -> Tag:
        """Converts a note body to a standard `<li>` and injects a backlink.

        This method transforms a raw note body tag (e.g., `<aside>`) into a
        standardized `<li>` element, ensuring it has the correct `id` and `role`
        attributes. It also calls `_ensure_backlink` to guarantee a backlink.

        Args:
            soup (BeautifulSoup): The root BeautifulSoup object, used to create new tags.
            note_body_tag (Tag): The BeautifulSoup `Tag` representing the original note body.
            index (int): The sequential index of the note, used for ID generation.
            callout_id (str): The ID of the corresponding callout, passed to `_ensure_backlink`.

        Returns:
            Tag: The newly created and populated `<li>` tag.

        Raises:
            None

        Mutations:
            - Creates a new `<li>` tag.
            - Calls `_ensure_backlink` which may modify `note_body_tag`.
            - Moves all child elements from `note_body_tag` into the new `<li>` tag.

        Rules & Limits:
            - New Tag: Creates an `<li>` tag.
            - ID Format: `fn-{index}`.
            - Role: `doc-endnote`.
        """
        li = soup.new_tag("li", id=f"fn-{index}", role="doc-endnote")
        self._ensure_backlink(
            soup,
            note_body_tag,
            callout_id,
        )

        for child in tuple(note_body_tag.children):
            li.append(child.extract())

        return li

    def _process_callouts(
        self,
        soup: BeautifulSoup,
        note_bodies: dict[str, Tag],
        collector: AnomalyCollector,
    ) -> tuple[dict[int, Tag], int, set[str]]:
        """Processes all callouts, matching them to bodies and standardizing them.

        This is the core loop for processing footnote callouts. It iterates through
        each callout, attempts to match it with an extracted note body, and then
        standardizes both the callout and the note body. It also tracks dangling
        references and returns the set of note body IDs that were successfully
        referenced.

        Args:
            soup (BeautifulSoup): The DOM tree containing the callouts.
            note_bodies (dict[str, Tag]): A dictionary of extracted note bodies,
                keyed by their original IDs.
            collector: The collector for anomalies.

        Returns:
            tuple[dict[int, Tag], int]: A tuple containing:
                - dict[int, Tag]: A dictionary of processed note bodies (as `<li>` tags),
                  keyed by their sequential index.
                - int: The total count of successfully processed notes.
                - set[str]: A set of the original note body IDs that were
                  successfully processed.

        Raises:
            None

        Mutations:
            - Modifies `callout` tags in-place via `_standardize_callout`.
            - Modifies `note_body_tag` in-place via `_standardize_note_body`.
        """
        if not self.callout_selector:
            log.warning(
                "Strategy %s has an empty callout_selector; cannot process callouts.",
                self.__class__.__name__,
            )
            return {}, 0, set()

        processed_notes: dict[int, Tag] = {}
        notes_count = 0
        used_target_ids: set[str] = set()

        # Cache endnote <li> IDs once to avoid repeated full-document CSS selection
        # inside the loop when checking for dangling references.
        endnote_li_ids: set[str] = set()
        if endnotes_section := soup.select_one("section[role='doc-endnotes']"):
            endnote_li_ids = {
                li_id
                for li in endnotes_section.select("li[id]")
                if (li_id := li.get("id")) and isinstance(li_id, str)
            }

        for i, callout in enumerate(soup.select(self.callout_selector), 1):
            raw_href = callout.get("href")
            normalized_href = normalize_href_attr(raw_href)

            if normalized_href is None:
                self._add_malformed_href_anomaly(
                    collector,
                    callout,
                    raw_href,
                    "Callout has a missing, empty, or invalid href attribute.",
                )
                continue

            if not normalized_href.startswith("#"):
                self._add_malformed_href_anomaly(
                    collector,
                    callout,
                    raw_href,
                    "Callout href does not reference an in-page note (must start with '#').",
                    normalized_href=normalized_href,
                )
                continue

            target_id = normalized_href.lstrip("#")
            if not target_id:
                self._add_malformed_href_anomaly(
                    collector,
                    callout,
                    raw_href,
                    "Callout href has an empty target ID (e.g., href='#').",
                )
                continue

            if target_id in note_bodies:
                notes_count += 1
                note_body_tag = note_bodies[target_id]
                used_target_ids.add(target_id)

                callout_id = self._standardize_callout(callout, i)
                li = self._standardize_note_body(
                    soup,
                    note_body_tag,
                    i,
                    callout_id,
                )
                processed_notes[i] = li
            elif target_id not in endnote_li_ids:
                self._add_dangling_ref_anomaly(collector, callout, target_id)
        return processed_notes, notes_count, used_target_ids

    def _rebuild_notes_section(
        self,
        soup: BeautifulSoup,
        processed_notes: dict[int, Tag],
    ) -> None:
        """Removes old note sections and appends a new, standardized one.

        This method ensures that the document contains a single, well-formed
        footnote section. It removes any existing footnote sections and then
        creates a new `<section>` containing an `<ol>` list, into which all
        processed note `<li>` elements are appended in numerical order.

        Args:
            soup (BeautifulSoup): The DOM tree to modify.
            processed_notes (dict[int, Tag]): A dictionary of processed note
                bodies (as `<li>` tags), keyed by their sequential index.

        Returns:
            None

        Raises:
            None

        Mutations:
            - Finds or creates a canonical `<section role="doc-endnotes">`.
            - Clears any existing `<ol>` inside this section to ensure idempotency.
            - Appends the processed note `<li>` tags in order to the `<ol>`.

        Rules & Limits:
            - If no `<body>` tag is found, a warning is logged, and the section
              is appended directly to the `soup` object.
        """
        if not processed_notes:
            return

        # Find or create the canonical notes section.
        notes_section = soup.select_one("section[role='doc-endnotes']")
        if not notes_section:
            notes_section = soup.new_tag("section", attrs={"role": "doc-endnotes"})
            if soup.body:
                soup.body.append(notes_section)
            else:
                log.warning("No <body> tag found to append the new notes section.")
                soup.append(notes_section)

        # Find the <ol>. If it exists, clear it to prevent duplicates. If not, create it.
        notes_ol = notes_section.select_one("ol")
        if notes_ol:
            notes_ol.clear()
        else:
            notes_ol = soup.new_tag("ol")
            notes_section.append(notes_ol)

        # Append the processed notes to the <ol> in order.
        for i in sorted(processed_notes.keys()):
            notes_ol.append(processed_notes[i])
