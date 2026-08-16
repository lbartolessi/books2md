"""A semantic enrichment layer for non-footnote DPUB-ARIA accessibility landmarks.

This module is responsible for intercepting specific accessibility attributes from
the original XHTML (epub:type and doc-* roles) and translating them into native
structural blocks or fenced blocks with semantic classes. This process is critical
for downstream RAG and LLM applications, as it isolates footnotes, filters
perimeter noise like bibliographies, and preserves page citations.

This module operates as a Stage 2 processor (Document Structure Layer) and does
not handle footnote/endnote vocabulary, which is the exclusive responsibility of
the `footnote_processor`.

Analytical Blueprint:
---------------------

Based on the specification, the following logic will be mapped to the class
methods:

Global Free Functions (Module Level):
    - None present in the skeleton.

Class Methods (AccessibilityNormalizer):
    - __init__: Initializes the normalizer with book-specific context and resets
      state counters for tracking changes: `page_breaks_anchored` (int),
      `bibliography_found` (bool), and `glossary_found` (bool).
    - process: Orchestrates the entire normalization pipeline. It first checks a
      guard clause to avoid processing content within code blocks. It then
      executes normalization sub-routines for page breaks, bibliographies, and
      glossaries, compiling metadata on completion.
    - _anchor_page_breaks: Finds all elements marked with `role="doc-pagebreak"`
      and replaces each with a `bs4.Comment` node. The comment's content is
      formatted as " page-break: {page_id} ", where `page_id` is extracted
      from the original element's 'id' or 'title' attribute. This preserves
      page milestone information for academic citation.
    - _wrap_landmark: A generic helper that finds all container elements marked
      with a specific `doc-*` role (e.g., `doc-bibliography`). For each element,
      it injects semantic classes and a data attribute to control downstream
      chunking.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final

from bs4 import BeautifulSoup, Comment, Tag
from bs4.element import PageElement

from .core import BookStyleContext, PipelineStatus
from .core.dom_utils import coerce_class_list, generate_processor_metadata


class AccessibilityNormalizer:
    """Orchestrates the normalization of non-footnote accessibility landmarks.

    This class is the main engine for processing DPUB-ARIA roles that are not
    related to footnotes. It identifies specific semantic landmarks like page breaks,
    bibliographies, and glossaries, and transforms them into standardized DOM
    structures that are optimized for downstream processing by RAG and LLM systems.

    The processor operates through a series of targeted mutations:
    - Page breaks (`doc-pagebreak`) are converted into structured comments to
      preserve citation milestones without disrupting text flow.
    - Bibliographies (`doc-bibliography`) and glossaries (`doc-glossary`) are
      wrapped in semantic containers with specific classes and data attributes
      to isolate them from the main narrative and guide the chunking process.

    This ensures that auxiliary content is semantically distinct from the primary
    text, improving the quality of data fed into language models.

    Attributes:
        context (BookStyleContext): The shared context for the book.
        page_breaks_anchored (int): A counter for the number of page break
            markers converted to comments.
        bibliography_found (bool): A flag indicating if a bibliography landmark
            was found.
        glossary_found (bool): A flag indicating if a glossary landmark was
            found.
    """

    _METADATA_KEY_PAGE_BREAKS = "page_breaks_anchored"
    _METADATA_KEY_LANDMARKS = "structural_landmarks_found"

    _LANDMARK_MAPPING: Final[dict[str, str]] = {
        "bibliography": "bibliography",
        "glossary": "glossary",
    }

    def __init__(self, context: BookStyleContext) -> None:
        """Initializes the AccessibilityNormalizer with book context and state.

        Args:
            context (BookStyleContext): The shared context for the book, providing
                access to configuration and helper methods like code block detection.

        Returns:
            None

        Raises:
            None

        Mutations:
            - Sets `self.context` to the provided context object.
            - Initializes `self.page_breaks_anchored` to 0.
            - Initializes `self.bibliography_found` to False.
            - Initializes `self.glossary_found` to False.

        Rules & Limits:
            - Instance Lifecycle: Assumes this instance is scoped to a single book and
              is never shared between different books, per Global Directive #3.
        """
        self.context = context
        self.page_breaks_anchored: int = 0
        self.bibliography_found: bool = False
        self.glossary_found: bool = False

    def process(self, soup: BeautifulSoup) -> tuple[BeautifulSoup, Mapping[str, Any]]:
        """Translates DPUB-ARIA landmarks into semantic DOM structures.

        This is the main entry point for the normalizer. It orchestrates the
        translation of non-footnote DPUB-ARIA landmarks (pagebreak, bibliography,
        glossary) into standardized DOM structures.

        Args:
            soup (BeautifulSoup): The in-memory DOM of the document to be processed.

        Returns:
            tuple[BeautifulSoup, Mapping[str, Any]]: A tuple containing the
                mutated soup object and a dictionary with metadata about the
                normalization process.
                The metadata includes counts of changes and a final status.
        Mutations:
            - The input `soup` object is modified in-place by the internal
              helper methods (`_anchor_page_breaks`, `_wrap_landmark`).

        Rules & Limits:
            - Execution Order: Internal methods are called in a strict sequence:
              1. `_anchor_page_breaks()`
              2. `_wrap_landmark()` for bibliographies.
              3. `_wrap_landmark()` for glossaries.
            - Immunity Protocol: The code block shield is applied on a per-node
              basis within each sub-method (`_anchor_page_breaks`, `_wrap_landmark`).
              This allows the normalizer to process documents that contain a mix
              of standard content and code blocks.
            - Status Logic: The final status is 'success' if any changes were made.
            - Metadata Contract: The returned dictionary conforms to the structure
              defined in the specification, including `page_breaks_anchored`,
              `structural_landmarks_found`, `status`, and `execution_timestamp`.
            - Full depth traversal: Yes.
        """
        # The immunity protocol is handled within each sub-method to check
        # individual nodes rather than the entire document at once.
        self._anchor_page_breaks(soup)

        landmarks_found: list[str] = []
        for role_name, css_class in self._LANDMARK_MAPPING.items():
            if self._wrap_landmark(soup, role_name, css_class):
                # Dynamically set the 'found' flag, e.g., self.bibliography_found = True
                setattr(self, f"{role_name}_found", True)
                landmarks_found.append(role_name)

        has_changes = self.page_breaks_anchored > 0 or bool(landmarks_found)
        status = PipelineStatus.SUCCESS if has_changes else PipelineStatus.SUCCESS_NOOP

        metrics = {
            self._METADATA_KEY_PAGE_BREAKS: self.page_breaks_anchored,
            self._METADATA_KEY_LANDMARKS: landmarks_found,
        }
        metadata = generate_processor_metadata(
            processor_key="accessibility_normalization",
            status=status,
            **metrics,
        )
        return soup, metadata

    def _anchor_page_breaks(self, soup: BeautifulSoup) -> None:
        """Finds and converts `doc-pagebreak` markers into structured comments.

        This method scans the DOM for elements with `role="doc-pagebreak"` and
        mutates them into `bs4.Comment` nodes. This preserves page location for
        citations without disrupting text flow. The `role` attribute can contain
        multiple space-separated values.

        Args:
            soup (BeautifulSoup): The in-memory DOM of the document.

        Returns:
            None

        Mutations:
            - Replaces `Tag` elements with `role="doc-pagebreak"` with new `Comment`
              objects within the `soup` object.
            - Increments the `self.page_breaks_anchored` instance counter for each
              marker found and replaced.

        Rules & Limits:
            - Target Attribute: Finds all elements where the `role` attribute is
              exactly "doc-pagebreak".
            - Page ID Source: The page identifier is retrieved from the element's `id`
              attribute. If `id` is not present, it falls back to the `title`
              attribute. If neither is present, it uses an empty string.
            - Comment Format: The generated comment's text is ` f" page-break: {page_id} " `
              with leading and trailing spaces.
            - Node Type Safety: The `soup.find_all` method ensures that only `Tag`
              objects (which have attributes) are processed, preventing errors on
              `NavigableString` nodes.
            - Full depth traversal: Yes.
        """
        # A static tuple is created to ensure safe iteration while modifying the DOM,
        # as `node.replace_with()` would invalidate a live iterator.
        # Filter directly for nodes whose role includes "doc-pagebreak" to avoid
        # scanning all role-bearing nodes on large documents.
        for node in tuple(
            soup.find_all(
                role=lambda v: bool(v and "doc-pagebreak" in coerce_class_list(v)),
            ),
        ):
            if self.context.is_inside_code_block(node):
                continue

            # Retrieve the page identifier from the 'id' or 'title' attribute.
            # If neither is present or both are empty, 'unknown' is used as a fallback
            # to preserve the page break marker while noting the missing data.
            page_id_val = node.get("id") or node.get("title")

            # Coerce the attribute value to a string, as bs4 can return a list or None.
            page_id_str = ""
            if isinstance(page_id_val, list):
                page_id_str = " ".join(map(str, page_id_val))
            elif page_id_val is not None:
                page_id_str = str(page_id_val)

            comment_text = f" page-break: {page_id_str.strip() or 'unknown'} "
            comment = Comment(comment_text)
            node.replace_with(comment)
            self.page_breaks_anchored += 1

    def _wrap_landmark(
        self,
        soup: BeautifulSoup,
        role_name: str,
        css_class: str,
    ) -> bool:
        """Finds and mutates a landmark container with semantic classes and attributes.

        This central primitive finds all elements with a specific `doc-*` role,
        injects semantic classes ('appendix-block' and a landmark-specific class),
        and adds a data attribute to control downstream chunking.

        Args:
            soup (BeautifulSoup): The in-memory DOM of the document.
            role_name (str): The name of the ARIA role (e.g., 'bibliography').
            css_class (str): The specific CSS class to add for this landmark.

        Returns:
            bool: True if any landmarks were found and mutated, False otherwise.
        """
        if not role_name or not css_class:
            return False

        changed = False
        target_role = f"doc-{role_name}"

        # Filter directly for nodes whose role includes the target role to avoid
        # scanning all role-bearing nodes on large documents.
        nodes_to_process = tuple(
            soup.find_all(
                role=lambda v: bool(v and target_role in coerce_class_list(v)),
            ),
        )
        for node in nodes_to_process:
            if self._process_single_landmark_node(node, target_role, css_class):
                changed = True
        return changed

    def _process_single_landmark_node(
        self,
        node: PageElement,
        target_role: str,
        css_class: str,
    ) -> bool:
        """Processes a single node, mutating it if it matches the landmark criteria.

        This helper checks if a node is a valid `Tag`, not inside a code block,
        and has the target role. If so, it injects the required classes and
        data attributes.

        Args:
            node (PageElement): The `PageElement` to process.
            target_role (str): The specific 'doc-*' role to match.
            css_class (str): The CSS class to add to the landmark.

        Returns:
            bool: True if the node was mutated, False otherwise.
        """
        if not isinstance(node, Tag) or self.context.is_inside_code_block(node):
            return False

        if target_role not in coerce_class_list(node.get("role")):
            return False

        node_classes = coerce_class_list(node.get("class"))

        # Add new classes if they don't exist, preserving order and avoiding duplicates.
        # This avoids reformatting the entire class attribute.
        if "appendix-block" not in node_classes:
            node_classes.append("appendix-block")
        if css_class not in node_classes:
            node_classes.append(css_class)

        node["class"] = " ".join(node_classes)
        node["data-chunk-strategy"] = "no_split"
        return True
