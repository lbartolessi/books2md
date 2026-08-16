"""A containment strategy for inconsistent or pattern-less footnote markup.

This module provides the `AnomalyStrategy`, which acts as a safety net (Stage C)
in the footnote processing pipeline. It is designed to surgically sanitize
several common, non-standard footnote-like structures that are not handled by
the more structured, pattern-based strategies. It targets specific, known
anomalies like inline notes, flat-text notes, and OCR artifacts.

Analytical Blueprint:
---------------------
- **Objective:** To identify and normalize several common, non-standard
  footnote-like structures that are not handled by pattern-based strategies.
  This strategy acts as a "cleanup" stage for known anomalies.
- **Components:**
  - `AnomalyStrategy`: The main class implementing the strategy.
  - `_resolve_inline_notes`: Handles notes embedded directly in text using
    `<span>` or `<small>` tags with superscript styling.
  - `_resolve_flat_text_notes`: Handles notes written as plain paragraphs at
    the end of a document, identified by a `[1]`-style prefix.
  - `_resolve_ocr_blocks`: Handles text blocks misplaced by OCR, identified by
    absolute positioning styles.
  - `_sanitize_dangling_refs`: Neutralizes internal links that point to
    non-existent IDs within the book.
- **Analytical Steps:**
  1. Scan the DOM for inline superscripted notes (`<span>`/`<small>`) that are
     not already links.
  2. Scan for paragraphs at the end of the document that match a flat-text
     note pattern (e.g., `[1] ...`).
  3. Scan for elements with absolute positioning styles indicative of OCR errors.
  4. Scan for all internal anchor links (`<a href="#...">`) and verify that
     their targets exist within the book's documents.
- **Transformation Rules:**
  - **Inline Notes:** The `<span>`/`<small>` tag is replaced with a standard
    `<a role="doc-noteref">` callout. A corresponding `<li>` note body is
    created and appended to the document's canonical footnote section.
  - **Flat-Text Notes:** The paragraphs are extracted, converted into `<li>`
    note bodies, and appended to the footnote section. Text in the main
    document matching the callout pattern (e.g., `[1]`) is replaced with a
    standard `<a role="doc-noteref">` link.
  - **OCR Blocks:** The absolute positioning styles are stripped from the
    element, allowing it to reflow with the document content.
  - **Dangling Refs:** The `<a>` tag is converted into a `<span>`, preserving
    the text but removing the broken hyperlink.
- **Output:**
  - A mutated `BeautifulSoup` object with the anomalies corrected.
  - A metadata dictionary reporting the types and counts of anomalies resolved.
"""

import logging
import re
from typing import Any

from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString

from dom_normalizer.core import BookStyleContext, PipelineStatus  # Keep this line
from dom_normalizer.core.dom_utils import coerce_class_list, get_utc_timestamp

from .base_strategy import (
    STRATEGY_PROCESSOR_UNBOUND_MSG,
    BaseFootnoteStrategy,
)  # Import the constant

log = logging.getLogger(__name__)


class AnomalyStrategy(BaseFootnoteStrategy):
    """A containment strategy (Stage C) for inconsistent or pattern-less markup.

    This strategy acts as a safety net before resorting to dynamic forensic
    triage. It applies surgical, in-place sanitation to resolve notes that
    violate the DOM specification or lack the minimum HTML scaffolding to be
    processed by static or parameterized strategies.
    """

    FLAT_NOTE_SEARCH_LIMIT: int = 50

    def __init__(self) -> None:
        """Initializes the AnomalyStrategy."""
        super().__init__()
        self.backlink_selector = 'a[role="doc-backlink"]'
        self._all_ids: set[str] | None = None

    def can_process(self, soup: BeautifulSoup, context: BookStyleContext) -> bool:
        """
        Evaluates if the document requires intervention to contain known anomalies.

        Scans the DOM for:
        1. Inline spans (`<span>`, `<small>`) with superscript styles but without
           anchors (inline).
        2. Final paragraphs that look like flat notes without anchor identifiers
           (flat-text).
        3. Elements with `style="position:absolute"` typical of broken OCR.
        4. Reference callouts (href anchors) that point to IDs that do not exist
           in the EPUB manifest (dangling-refs).

        Args:
            soup (BeautifulSoup): The instantiated DOM tree of the source file.
            context (BookStyleContext): The configuration and telemetry context.

        Returns:
            bool: True if any cataloged anomaly is detected; False otherwise.
        """
        # 1. Inline notes (span/small with super style, not in an <a>)
        # This regex should match the start of a potential inline note, e.g., "1. Note text..."
        inline_note_pattern = re.compile(r"^\s*(\d+)\.\s*(.*)", re.DOTALL)
        for tag in soup.find_all(
            ["span", "small"],
            style=re.compile(r"vertical-align:\s*super"),
        ):
            if tag.find_parent("a"):
                continue
            text = tag.get_text(strip=True)
            if inline_note_pattern.match(text):
                return True

        if flat_note_ps := soup.find_all("p"):
            last_ps = flat_note_ps[-self.FLAT_NOTE_SEARCH_LIMIT :]
            if any(re.match(r"^\s*\[\d+\]", p.get_text()) for p in reversed(last_ps)):
                return True

        # 3. OCR blocks
        return bool(soup.select_one('[style*="position:absolute"]'))

    def process(
        self,
        soup: BeautifulSoup,
        context: BookStyleContext,
        all_soups: dict[str, BeautifulSoup] | None = None,
        current_soup_key: str | None = None,
    ) -> tuple[BeautifulSoup, dict[str, Any]]:
        """Sanitizes and restructures anomalous markup fragments in the DOM in-place.

        It sequentially delegates to specific resolution sub-methods and
        accumulates a log of the interventions performed for telemetry.

        Args:
            soup (BeautifulSoup): The anomalous DOM tree to mutate.
            context (BookStyleContext): Context providing access to global link
                                        validation tools.

        Returns:
            Tuple[BeautifulSoup, dict[str, Any]]:
                - BeautifulSoup: The DOM tree with the anomalies resolved.
                - dict: A telemetry dictionary, where `anomalies_detected` is
                        a list of the corrected anomalies (e.g., ["inline", "ocr"]).
        Calls:
            - `_resolve_ocr_blocks`: To handle OCR-related anomalies.
            - `_resolve_inline_notes`: To extract and standardize inline notes.
            - `_resolve_flat_text_notes`: To process flat-text notes at the end of sections.
            - `_sanitize_dangling_refs`: To convert broken links to spans.
            - `get_utc_timestamp`: To record the execution time.
        """
        # pylint: disable=unused-argument
        anomalies_payload = []

        start_time = get_utc_timestamp()

        ocr_count = self._resolve_ocr_blocks(soup)
        if ocr_count > 0:
            anomalies_payload.append(
                {"key": "ocr", "message": f"Resolved {ocr_count} OCR block(s)."},
            )

        inline_count = self._resolve_inline_notes(soup)
        if inline_count > 0:
            anomalies_payload.append(
                {
                    "key": "inline",
                    "message": f"Resolved {inline_count} inline note(s).",
                },
            )

        flat_count = self._resolve_flat_text_notes(soup)
        if flat_count > 0:
            anomalies_payload.append(
                {
                    "key": "flat-text",
                    "message": f"Resolved {flat_count} flat-text note(s).",
                },
            )

        dangling_count = self._sanitize_dangling_refs(soup, all_soups)
        if dangling_count > 0:
            anomalies_payload.append(
                {
                    "key": "dangling-refs",
                    "message": f"Sanitized {dangling_count} dangling reference(s).",
                },
            )

        # `notes_created_count` tracks only actual footnote bodies created.
        notes_created_count = inline_count + flat_count
        # Any repair, including creating notes, fixing OCR, or sanitizing links,
        # indicates that the strategy performed meaningful work.
        total_anomalies_fixed = notes_created_count + ocr_count + dangling_count
        status = (
            PipelineStatus.SUCCESS
            if total_anomalies_fixed > 0
            else PipelineStatus.SUCCESS_NOOP
        )
        return soup, BaseFootnoteStrategy.create_metadata(
            strategy_name="AnomalyStrategy",
            status=status,
            notes_processed_count=notes_created_count,
            notes_found_count=notes_created_count,
            notes_rebuilt_count=notes_created_count,
            backlinks_injected_count=notes_created_count,
            anomalies=anomalies_payload,
            anomalies_repaired_count=total_anomalies_fixed,
            start_time=start_time,
        )

    def _get_or_create_notes_section(self, soup: BeautifulSoup) -> Tag:
        """Finds or creates the main <ol> for footnotes.

        This helper method ensures that there is a canonical `<ol>` element
        within a `<section class="footnotes" role="doc-endnotes">` to append
        standardized footnote `<li>` elements. If such a structure doesn't exist,
        it creates it and appends it to the `<body>` of the document.

        Args:
            soup (BeautifulSoup): The BeautifulSoup object representing the DOM.

        Returns:
            Tag: The `<ol>` tag where footnote `<li>` elements should be appended.

        Raises:
            None

        Mutations:
            - May create and append a new `<section>` and `<ol>` to the `soup.body`.

        Rules & Limits:
            - If no `<body>` tag is found, a warning is logged, and the section
              is appended directly to the `soup` object.
            - Ensures the returned `Tag` is always an `<ol>` element.
        """
        notes_section = soup.select_one("section[role='doc-endnotes']")
        if not notes_section:
            notes_section = soup.new_tag("section", attrs={"role": "doc-endnotes"})
            ol_tag = soup.new_tag("ol")
            notes_section.append(ol_tag)
            if soup.body:
                soup.body.append(notes_section)
            else:
                log.warning(
                    "No <body> tag found to append notes section for anomalies.",
                )
                soup.append(notes_section)

        ol_tag = notes_section.select_one("ol")
        if not ol_tag:
            ol_tag = soup.new_tag("ol")
            notes_section.append(ol_tag)
        return ol_tag

    def _resolve_inline_notes(self, soup: BeautifulSoup) -> int:
        """Extracts illegally embedded text from the paragraph flow and converts it
        into a valid note structure in a lower block, synthesizing its IDs.

        Args:
            soup (BeautifulSoup): The current DOM.
        Returns:
            int: The number of inline notes extracted and resolved.

        Calls:
            - `_get_or_create_notes_section`: To ensure a target for new notes.
            - Creates new `<li>` and `<a>` tags for the note body and backlink.

        """
        count = 0
        notes_ol: Tag | None = None  # Lazy initialization
        assert self.processor, STRATEGY_PROCESSOR_UNBOUND_MSG

        start_index = 0

        # A static tuple is created to ensure safe iteration while modifying the DOM,
        # as `tag.replace_with()` would invalidate a live iterator.
        candidates = tuple(
            tag
            for tag in soup.find_all(
                ["span", "small"],
                style=re.compile(r"vertical-align:\s*super"),
            )
            if not tag.find_parent("a")
        )

        # Regex is tightened to require a dot after the number to avoid
        # misclassifying other superscripted numbers as notes.
        note_pattern = re.compile(r"^\s*(\d+)\.\s*(.*)", re.DOTALL)

        for tag in candidates:
            match = note_pattern.match(tag.get_text(strip=True))
            if not match:
                continue

            # First time a valid note is found, create the section.
            if notes_ol is None:
                notes_ol = self._get_or_create_notes_section(soup)
                start_index = len(notes_ol.find_all("li"))

            count += 1
            current_index = start_index + count
            note_number, note_text = match.groups()

            # Create and standardize the callout
            callout = soup.new_tag(
                "a",
                id=f"fnref-anomaly-inline-{current_index}",
                href=f"#fn-anomaly-inline-{current_index}",
                role="doc-noteref",
            )
            tag.replace_with(callout)
            callout.string = note_number

            # Create and standardize the note body
            li = soup.new_tag(
                "li",
                id=f"fn-anomaly-inline-{current_index}",
                role="doc-endnote",
            )
            p_tag = soup.new_tag("p")
            p_tag.string = note_text.strip()
            li.append(p_tag)

            # Ensure a canonical backlink is present
            self._ensure_backlink(soup, li, str(callout["id"]))

            assert notes_ol is not None
            notes_ol.append(li)
        return count

    def _find_flat_note_block(self, soup: BeautifulSoup) -> list[Tag]:
        """
        Scans backwards from the end of the body to find a contiguous block of
        paragraphs that appear to be flat-text footnotes.

        Args:
            soup (BeautifulSoup): The document's DOM.

        Returns:
            list[Tag]: A list of candidate paragraph tags, in document order.
        """
        if not soup.body:
            return []

        # Heuristically limit search to the last 50 paragraphs in document
        # order to avoid scanning the entire document while still detecting
        # notes that are wrapped inside containers (e.g., &lt;section&gt;, &lt;div&gt;).
        candidate_ps = soup.find_all("p")
        candidate_ps = candidate_ps[-self.FLAT_NOTE_SEARCH_LIMIT :]
        flat_note_block = []
        note_pattern = re.compile(r"^\s*\[(\d+)\]")
        for p in reversed(candidate_ps):
            if note_pattern.match(p.get_text()):
                flat_note_block.insert(0, p)
            elif not flat_note_block:
                # Still searching for the start of the block
                continue
            else:
                # Found the start of the block, so stop.
                break
        return flat_note_block

    def _process_flat_note_bodies(
        self,
        soup: BeautifulSoup,
        flat_note_block: list[Tag],
        notes_ol: Tag,
    ) -> tuple[dict[str, str], int]:
        """
        Converts a block of flat-text note paragraphs into a canonical list
        and returns a map for linking callouts.

        Args:
            soup (BeautifulSoup): The root BeautifulSoup object.
            flat_note_block (list[Tag]): The list of paragraph tags to process.
            notes_ol (Tag): The ordered list element to append notes to.

        Returns:
            tuple[dict[str, str], int]: A tuple containing:
                - A map from the note number (e.g., '1') to the new note ID.
                - The count of processed notes.
        """
        callout_map = {}
        count = 0
        start_index = len(notes_ol.find_all("li"))
        note_pattern = re.compile(r"^\s*\[(\d+)\]\s*(.*)", re.DOTALL)

        for p in flat_note_block:
            match = note_pattern.match(p.get_text())
            if not match:
                continue

            assert self.processor, STRATEGY_PROCESSOR_UNBOUND_MSG
            count += 1
            current_index = start_index + count
            note_number, note_text = match.groups()

            note_id = f"fn-flat-{current_index}"
            li = soup.new_tag("li", role="doc-endnote", id=note_id)
            li.string = note_text.strip()
            notes_ol.append(li)

            callout_map[note_number] = note_id
            p.decompose()
        return callout_map, count

    def _build_replacement_elements(
        self,
        text: str,
        callout_map: dict[str, str],
        soup: BeautifulSoup,
    ) -> list[str | Tag] | None:
        """Builds a list of replacement nodes for a text string with callouts."""
        new_elements: list[str | Tag] = []
        last_index = 0
        has_match = False

        for match_obj in re.finditer(r"\[(\d+)\]", text):
            note_number = match_obj.group(1)
            if note_number in callout_map:
                has_match = True
                new_elements.append(text[last_index : match_obj.start()])
                callout_tag = soup.new_tag(
                    "a",
                    role="doc-noteref",
                    href=f"#{callout_map[note_number]}",
                )
                callout_tag.string = f"[{note_number}]"
                new_elements.append(callout_tag)
                last_index = match_obj.end()

        if not has_match:
            return None

        new_elements.append(text[last_index:])
        return new_elements

    def _replace_node_with_elements(
        self,
        original_node: NavigableString,
        new_elements: list[str | Tag],
    ) -> None:
        """Replaces a node with a sequence of new elements."""
        # The `replace_with` method can take multiple arguments and will
        # replace the original node with the sequence of new nodes.
        # We use the splat operator (*) to unpack the list.
        original_node.replace_with(*new_elements)

    def _link_flat_note_callouts(
        self,
        soup: BeautifulSoup,
        callout_map: dict[str, str],
    ) -> None:
        """Scans text nodes, finds callouts (e.g., '[1]'), and replaces them with links."""
        if not soup.body:
            return

        # A static tuple is created to ensure safe iteration while modifying the DOM,
        # as `_replace_node_with_elements` will decompose text nodes.
        # Find all text nodes in the document body
        for text_node in tuple(soup.body.find_all(string=True)):
            if text_node.parent and (
                text_node.parent.name in ["style", "script", "a"]
                or "[" not in str(text_node)
            ):
                continue

            if new_elements := self._build_replacement_elements(
                str(text_node),
                callout_map,
                soup,
            ):
                self._replace_node_with_elements(text_node, new_elements)

    def _resolve_flat_text_notes(self, soup: BeautifulSoup) -> int:
        """Locates paragraphs at the end of the section that act as notes and
        injects return identifiers by pairing them with possible callouts in the text.

        Args:
            soup (BeautifulSoup): The current DOM.
        Returns:
            int: The number of normalized flat-text notes.

        Calls:
            - `_find_flat_note_block`: To identify potential flat-text note paragraphs.
            - `_get_or_create_notes_section`: To ensure a target for new notes.
            - `_process_flat_note_bodies`: To convert identified paragraphs into `<li>` elements.
            - `_link_flat_note_callouts`: To create links from text callouts to the new notes.
        """
        if not soup.body:
            return 0

        flat_note_block = self._find_flat_note_block(soup)
        if not flat_note_block:
            return 0

        notes_ol = self._get_or_create_notes_section(soup)
        callout_map, count = self._process_flat_note_bodies(
            soup,
            flat_note_block,
            notes_ol,
        )

        if callout_map:
            assert self.processor, (
                "Strategy has not been bound to a processor instance."
            )
            assert self.processor, STRATEGY_PROCESSOR_UNBOUND_MSG
            self._link_flat_note_callouts(soup, callout_map)

        return count

    def _strip_positioning_styles(self, tag: Tag) -> None:
        """Removes all inline styling from a potential OCR block.

        In line with the project's "iconoclast" philosophy, this method
        radically removes the entire `style` attribute from the tag. This ensures
        that all presentational styling is stripped, leaving only the structural
        and semantic content, which is the desired behavior for OCR block repair.

        Args:
            tag: The BeautifulSoup `Tag` whose style attribute will be modified.

        Mutations:
            - Deletes the `style` attribute from the `tag` if it exists.
        """
        if "style" in tag.attrs:
            del tag.attrs["style"]

    def _resolve_ocr_blocks(self, soup: BeautifulSoup) -> int:
        """Removes absolute CSS positioning from broken OCR text blocks and,
        where appropriate, reintegrates them into the relative structural flow
        of sequential reading.

        Args:
            soup (BeautifulSoup): The current DOM.
        Returns:
            int: The number of repositioned OCR blocks.
        """
        count = 0
        # A static tuple is created to ensure safe iteration while modifying the DOM,
        # as `tag.extract()` would invalidate a live iterator.
        ocr_candidates = tuple(
            soup.select(
                '[style*="position:absolute"][class*="ocr"], '
                '[style*="position:absolute"][data-ocr-block]',
            ),
        )

        for tag in ocr_candidates:
            # Strip positioning styles and let the block reflow in its original position.
            # No extraction or re-insertion is performed to preserve local context.
            self._strip_positioning_styles(tag)
            count += 1
        return count

    def _sanitize_dangling_refs(
        self,
        soup: BeautifulSoup,
        all_soups: dict[str, BeautifulSoup] | None = None,
    ) -> int:
        """Identifies <a> tags whose references (href) do not exist in the entire
        book environment. Instead of failing, it converts the broken link into a
        semantic `<span>`, preserving the visual text but removing the dead hyperlink.

        Args:
            soup (BeautifulSoup): The current DOM.
            all_soups (dict[str, BeautifulSoup] | None): A dictionary mapping all
                file keys to their soup objects, for cross-file validation.

        Returns:
            int: The number of sanitized dangling references.
        """
        count = 0

        # Pre-compute a global ID index for all soups to avoid O(N*M) scanning.
        # The index is cached on the strategy instance for the lifetime of the book processing.
        all_ids: set[str] | None = None
        if all_soups:
            if self._all_ids is None:
                self._all_ids = {
                    element_id
                    for other_soup in all_soups.values()
                    for element in other_soup.select("[id]")
                    if (element_id := element.get("id")) and isinstance(element_id, str)
                }
            all_ids = self._all_ids

        # A static tuple is created to ensure safe iteration while modifying the DOM,
        # as `link.name` assignment would invalidate a live iterator.
        for link in tuple(soup.select('a[href^="#"]')):
            target_id = link["href"][1:]

            target_found = False
            # Check current soup first for efficiency
            if soup.find(id=target_id) or (
                all_ids is not None and target_id in all_ids
            ):
                target_found = True

            if not target_found:
                # Preserve the <a> tag but mark it as broken.
                classes = coerce_class_list(link.get("class"))
                classes.append("broken-link")
                link["class"] = " ".join(classes)
                del link["href"]
                count += 1
        return count
