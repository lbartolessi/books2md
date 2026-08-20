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
from collections.abc import Mapping, Sequence
from pathlib import Path  # type: ignore
from typing import Any

from bs4 import BeautifulSoup, Tag
from bs4.element import PageElement

from .core import (
    BookStyleContext,
    PipelineStatus,
)
from .core.component_registry import register_processor_factory
from .core.config import EngineConfiguration
from .core.dom_utils import (
    coerce_class_list,
    find_all_snapshot,
    generate_processor_metadata,
    is_ignorable_node,
)
from .core.navigation_utils import (
    FILE_FALLBACK_RX,
    extract_trailing_numbers_from_block,
    get_final_column_numeric_values,
    get_toc_line_rx,
    initial_column_has_short_text,
    is_arithmetic_progression,
    is_strictly_non_decreasing,
)

log = logging.getLogger(__name__)


class NavigationPurger:
    """A multi-pillar engine for detecting and purging redundant navigation structures."""

    _FILE_FALLBACK_RX = FILE_FALLBACK_RX


    def __init__(
        self,
        context: BookStyleContext,
    ) -> None:
        """Initializes the navigation purger with context and telemetry.

        Args:
            context (BookStyleContext): The shared context for the book.

        Returns:
            None

        Raises:
            None

        Mutations:
            - Initializes `self.context` to the provided context object.
            - Initializes `self.native_toc_isolated` to `False`.
            - Initializes `self.nav_elements_purged` to 0.
            - Initializes `self.inline_toc_blocks_purged` to 0.
            - Initializes `self.tabular_indexes_purged` to 0.
            - Initializes `self.chars_removed_count` to 0.
            - Initializes `self.elements_evaluated_count` to 0.

        Rules & Limits:
            - Instance Lifecycle: Assumes this instance is scoped to a single book,
              per Global Directive #3.
        """
        self.context = context # type: ignore
        self.config: EngineConfiguration = context.config
        self._toc_line_rx = get_toc_line_rx(self.config)
        self.native_toc_isolated: bool = False
        self.nav_elements_purged: int = 0
        self.inline_toc_blocks_purged: int = 0
        self.tabular_indexes_purged: int = 0
        self.chars_removed_count: int = 0
        self.elements_evaluated_count: int = 0

    def process(self, soup: BeautifulSoup, file_path: Path) -> tuple[BeautifulSoup, Mapping[str, Any]]:
        """Executes the full three-pillar navigation purging process.

        This is the main entry point. It orchestrates the detection and purging
        of semantic TOCs, inline TOCs, and tabular indexes in a strict sequence.

        Args:
            soup (BeautifulSoup): The in-memory DOM of the document to be processed.
            file_path (Path): The path to the current HTML file.

        Returns:
            tuple[BeautifulSoup, Mapping[str, Any]]: A tuple containing the mutated
                soup object and a dictionary with metadata about the normalization process.

        Raises:
            Exception: Per Global Directive #1, any unexpected native exceptions
                during processing will be caught, logged as CRITICAL, and re-raised.

        Mutations:
            - The input `soup` object is modified in-place by the various purging
              helper methods.

        Rules & Limits:
            - Execution Order: Internal methods are called in a strict sequence:
              1. `_purge_native_and_fallback_tocs(soup)`
              2. `_purge_inline_toc_blocks(soup)`
              3. `_purge_tabular_indexes(soup)`
            - Pipeline Order Contract: This processor must run after `structural_sanitizer`
              and before `floating_element_processor`.
            - Full depth traversal: Yes.
        """
        # Pillar 1 & Tier 2 Fallback
        self._purge_native_and_fallback_tocs(soup, file_path)

        # If a full-file purge happened, the body is empty. No need to run other pillars.
        if self.native_toc_isolated:
            status = PipelineStatus.SUCCESS
            return soup, self.get_metadata(status)

        # Pillar 2
        self._purge_inline_toc_blocks(soup)
        # Pillar 3
        self._purge_tabular_indexes(soup)
        # New: Purge elements based on link density heuristic
        self._purge_high_link_density_elements(soup)

        has_changes = (
            self.native_toc_isolated
            or self.nav_elements_purged > 0
            or self.inline_toc_blocks_purged > 0
            or self.tabular_indexes_purged > 0
        )
        status = PipelineStatus.SUCCESS if has_changes else PipelineStatus.SUCCESS_NOOP
        return soup, self.get_metadata(status)

    def _purge_nodes(
        self,
        soup: BeautifulSoup,
        nodes_to_purge: Sequence[PageElement],
    ) -> None:
        """Decomposes a list of nodes and updates the character removal count.

        Args:
            soup (BeautifulSoup): The root BeautifulSoup object of the document.
            nodes_to_purge (Sequence[PageElement]): A sequence of `bs4.PageElement`
                objects to remove from the DOM.

        Returns:
            None

        Raises:
            None

        Mutations:
            - Decomposes each `Tag` in `nodes_to_purge` from the DOM tree.
            - Increments `self.chars_removed_count` by the text length of each
              decomposed node.

        Rules & Limits:
            - Node Type Safety: This function only acts on `Tag` instances,
              ignoring other `PageElement` types like `NavigableString` to
              prevent potential attribute errors.
            - Character Count Accuracy: The `chars_removed_count` is calculated
              by summing the text length of each node before it is purged, and then
              adding the difference in total document length.

        """
        initial_text_len = len(soup.get_text())
        for node in nodes_to_purge:
            if isinstance(node, Tag):
                self.chars_removed_count += len(node.get_text())
                node.decompose()
        final_text_len = len(soup.get_text())
        self.chars_removed_count += initial_text_len - final_text_len

    def _handle_tier2_fallback_purge(
        self,
        soup: BeautifulSoup,
        file_path: Path,
    ) -> bool:
        """Implements the Tier 2 file-based fallback purge logic.

        This method calculates the Text-to-Link Character Ratio (TLCR) for the
        document's body. Based on the TLCR and the presence of protected prose
        containers, it either purges the entire body or delegates to finer-grained
        purging methods.

        Args:
            soup (BeautifulSoup): The DOM of the file being processed.
            file_path (Path): The path to the current HTML file.

        Returns:
            bool: `True` if a purge action was taken (i.e., the body was cleared),
                `False` otherwise (delegated to micro-structural scanning).

        Raises:
            Exception: Per Global Directive #1, any unexpected native exceptions
                will be caught, logged as CRITICAL, and re-raised.

        Mutations:
            - If in "Pure Index Mode", the entire content of the `<body>` tag is
              cleared.
            - Increments `self.chars_removed_count` with the length of the cleared body.

        Rules & Limits:
            - Anti-Decomposition Guard: Before TLCR evaluation, the method MUST check
              for any container elements with the classes "prose", "editorial", or
              "editorial-prose" using `coerce_class_list`. If found, the file is
              forced into "Mixed Content Mode".
            - TLCR Calculation: TLCR = (Character count outside any <a> tag) / (Total
              character count within the <body>).
            - Pure Index Mode: Activated if `TLCR < 0.85` AND no protected prose
              containers are found. Action: Purge `<body>`.
            - Mixed Content Mode: Activated if `TLCR >= 0.85` OR protected prose
              containers are present. Action: Abort body purge and return `False`.
        """
        if not soup.body:
            return False

        # Anti-Decomposition Guard
        for tag in soup.body.find_all(True):
            classes = coerce_class_list(tag.get("class"))
            if self.config.protected_prose_classes.intersection(classes):
                return False  # Mixed Content Mode, abort body purge

        # TLCR Calculation
        total_chars = len(soup.body.get_text())
        if total_chars == 0:
            return False

        anchor_chars = sum(len(a.get_text()) for a in soup.body.find_all("a"))
        log.debug(
            "TLCR calculation: total_chars=%d, anchor_chars=%d",
            total_chars, # pyright: ignore[reportUnknownArgumentType]
            anchor_chars,
        )

        # If the entire body is composed of link text, it's ambiguous.
        # Let other pillars decide instead of performing an aggressive purge.
        if total_chars > 0 and total_chars == anchor_chars:
            return False

        tlcr = (total_chars - anchor_chars) / total_chars # pyright: ignore[reportUnknownVariableType]
        log.debug(
            "TLCR for file %s: %.2f (Threshold: %.2f)",
            file_path.name,
            tlcr,
            self.config.tlcr_threshold,
        )

        if tlcr < self.context.config.tlcr_threshold:  # Pure Index Mode
            log.debug(
                "Entering Pure Index Mode: Purging entire body for file %s.",
                file_path.name,
            )
            # The body is cleared directly to ensure all nodes, including
            # NavigableStrings, are removed correctly.
            self.chars_removed_count += len(soup.body.get_text())
            soup.body.clear()
            return True
        log.debug(
            "Entering Mixed Content Mode: Not purging body for file %s.",
            file_path.name,
        )
        return False

    def _purge_native_and_fallback_tocs(
        self,
        soup: BeautifulSoup,
        file_path: Path,
    ) -> bool:
        r"""Implements Pillar 1: Purges native EPUB3 TOCs and handles file-based fallback.

        Args:
            soup (BeautifulSoup): The in-memory DOM of the document.
            file_path (Path): The path to the current HTML file.

        Returns:
            bool: `True` if a native TOC was found and purged or if a Tier 2
                fallback purge occurred, `False` otherwise.

        Raises:
            Exception: Per Global Directive #1, any unexpected native exceptions
                will be caught, logged as CRITICAL, and re-raised.

        Mutations:
            - Decomposes elements matching Tier 1 semantic selectors.
            - May trigger a full body purge via `_handle_tier2_fallback_purge`.
            - Increments `self.nav_elements_purged` if a Tier 1 or Tier 2
              purge occurs.

        Rules & Limits:
            - Tier 1 Selectors: `[epub\\:type="toc"]`, `[role="doc-toc"]`, `nav`,
              `[role="navigation"]`, `.menu`, `.toc`.
            - Tier 2 File Fallback: If the document's file path matches the regex
              `r'/(nav|toc|indice|contents|summary)\.e?xhtml$'`, and no Tier 1
              TOC was found, `_handle_tier2_fallback_purge` is called.
        """
        # Expanded selector to include role="navigation" and common class names
        if native_tocs := soup.select( # type: ignore
            '[epub\\:type="toc"], [role="doc-toc"], nav, [role="navigation"], .menu, .toc',
        ):
            self._purge_nodes(soup, native_tocs)
            self.nav_elements_purged += len(native_tocs)
            return True

        # Tier 2 File Fallback
        # This fallback also counts as purging navigation elements.
        if self._FILE_FALLBACK_RX.search(
            file_path.as_posix(),
        ) and self._handle_tier2_fallback_purge(soup, file_path):
            self.native_toc_isolated = True
            return True
        return False

    def _is_potential_toc_line(self, node: PageElement) -> bool:
        r"""Checks if a node's text matches the inline TOC line pattern (Pillar 2).

        Args:
            node (PageElement): The node to evaluate.

        Returns:
            bool: `True` if the node is a potential TOC line, `False` otherwise.

        Raises:
            None

        Mutations:
            None.

        Rules & Limits:
            - Code Shield: Returns `False` if `self.context.is_inside_code_block(node)`
              is `True`.
            - Regex Match: Returns `True` if the node's stripped text matches the
              regex `r'^.{3,70}(?:\.{2,}|\s+|\-+|(?<!\d)\.)\d+(?:[\s,;\-]*\d*)\s*$'`.
            - Node Type Safety: Expects a `Tag`. Behavior on a `NavigableString` is
              valid as it can be converted to text.
        """
        if not isinstance(node, Tag) or self.context.is_inside_code_block(node):
            return False
        text = node.get_text(strip=True)
        return bool(self._toc_line_rx.match(text))

    def _should_stop_gathering_block(self, sibling: Tag) -> bool:
        """Checks if the block gathering process should stop based on air-lock conditions.

        Args:
            sibling (Tag): The sibling tag to evaluate.

        Returns:
            bool: True if the gathering should stop, False otherwise.
        """
        return ( # pyright: ignore[reportUnknownArgumentType]
            sibling.name == "h2"
            or len(sibling.get_text().split()) > self.config.max_words_in_toc_airlock
        )

    def _get_toc_line_from_wrapper(self, wrapper_tag: Tag) -> Tag | None:
        """If a tag is a simple wrapper, returns the potential TOC line inside.

        A simple wrapper is defined as a <div> containing a single child element
        that is itself a potential TOC line.

        Args:
            wrapper_tag (Tag): The potential wrapper tag to inspect.

        Returns:
            Tag | None: The inner TOC line tag if found, otherwise None.
        """
        if wrapper_tag.name == "div" and len(wrapper_tag.contents) == 1:
            inner_node = wrapper_tag.contents[0]
            if isinstance(inner_node, Tag) and self._is_potential_toc_line(
                inner_node,
            ):
                return inner_node
        return None

    def _gather_potential_toc_block(self, start_node: Tag) -> list[Tag]:
        """Gathers a contiguous block of sibling nodes that look like TOC lines.

        Starting from `start_node`, this method traverses forward through siblings,
        collecting a list of nodes that are potential TOC lines. It robustly
        handles shallow wrapper tags by iterating through the parent's children
        instead of relying on `next_sibling`.

        Args:
            start_node (Tag): The starting node of the potential block.

        Returns:
            list[Tag]: A list of contiguous nodes forming the potential block.
        """
        current_block = [start_node]
        parent = start_node.parent
        if not (parent and hasattr(parent, "contents")):
            return current_block  # Fallback for nodes without a proper parent

        try:
            start_index = parent.contents.index(start_node)
        except ValueError:
            return current_block  # Should not happen if parent is correct

        for sibling in parent.contents[start_index + 1 :]:
            if is_ignorable_node(sibling, self.config):
                continue

            if not isinstance(sibling, Tag):
                break  # Non-tag elements break contiguity

            # Air-Lock conditions to stop the run.
            if self._should_stop_gathering_block(sibling): # pyright: ignore[reportUnknownArgumentType]
                break

            if self._is_potential_toc_line(sibling):
                current_block.append(sibling)
                continue

            # If the sibling is not a TOC line, but it's a simple wrapper
            # (e.g., a div with one child), check inside.
            if toc_line_in_wrapper := self._get_toc_line_from_wrapper(sibling):
                current_block.append(toc_line_in_wrapper)
                continue

            # If not a TOC line and not a simple wrapper containing one, stop.
            break
        return current_block

    def _purge_inline_toc_blocks(self, soup: BeautifulSoup) -> None:
        """Finds and purges contiguous blocks of inline TOC lines (Pillar 2).

        This method implements a sliding-window sweep to group and evaluate
        potential inline tables of contents.

        Args:
            soup (BeautifulSoup): The in-memory DOM of the document.

        Returns:
            None

        Raises:
            Exception: Per Global Directive #1, any unexpected native exceptions
                will be caught, logged as CRITICAL, and re-raised.

        Mutations:
            - May purge blocks of nodes via `_evaluate_and_purge_toc_block`.

        Rules & Limits:
            - Traversal: Iterates through all nodes in the document.
            - Sliding Window: Gathers contiguous sibling nodes for which
              `_is_potential_toc_line` is `True`.
            - Air-Lock: A run of candidates is aborted if it hits a text block
              with > 30 words, an `<h2>` tag, or a parent container boundary.
            - State Management: Maintains a set of processed nodes to avoid
              re-evaluating nodes that have already been purged.
            - Full depth traversal: Yes.
        """
        processed_nodes: set[Tag] = set()
        # More efficient to only check paragraphs and divs as starting points
        for start_node in soup.find_all(
            [
                "p",
                "div",
                "h1",
                "h2",
                "h3",
                "h4",
                "h5",
                "h6",
                "li",
            ],
        ):
            if start_node in processed_nodes or self.context.is_inside_code_block(
                start_node,
            ):
                continue

            if self._is_potential_toc_line(start_node) and (  # NOSONAR
                current_block := self._gather_potential_toc_block(start_node) # pyright: ignore[reportUnknownArgumentType]
            ):
                self._evaluate_and_purge_toc_block(soup, current_block)
                processed_nodes.update(current_block)

    def _evaluate_and_purge_toc_block(
        self,
        soup: BeautifulSoup,
        block: list[Tag],
    ) -> None:
        """Evaluates a candidate TOC block and purges it if it's not a checklist.

        Args:
            soup (BeautifulSoup): The root BeautifulSoup object.
            block (list[Tag]): The contiguous block of candidate nodes.

        Returns:
            None

        Mutations:
            - If the block is a valid TOC, it is purged via `_purge_nodes`.
            - Increments `self.inline_toc_blocks_purged` if a purge occurs.

        Rules & Limits:
            - Threshold Gate: The block is preserved if it contains fewer than 4 lines.
            - Anti-Step Guard: For blocks with >= 4 lines, the trailing numbers are
              extracted and checked with `_is_arithmetic_progression`. If it returns
              `True`, the block is preserved. Otherwise, it is purged. # pyright: ignore[reportUnusedMethod]
        """
        if len(block) < self.config.min_inline_toc_lines:
            return # pyright: ignore[reportUnusedMethod]

        numbers = extract_trailing_numbers_from_block(block)
        if numbers is not None and is_arithmetic_progression(
            numbers,
            self.config.min_inline_toc_lines,
            self.config,
        ):
            return  # Preserve checklists
        self._purge_nodes(soup, block)
        self.inline_toc_blocks_purged += 1

    def _is_potential_tabular_index(self, table: Tag) -> bool:
        """Evaluates if a `<table>` is an index based on Pillar 3's strict rules.

        Args:
            table (Tag): The `<table>` tag to evaluate.

        Returns:
            bool: `True` if the table is certified as an index, `False` otherwise.

        Mutations:
            - Increments `self.elements_evaluated_count`.

        Rules & Limits:
            - A table is an index if and only if all of the following are true:
              1. **Row Count Gate:** It contains at least 2 `<tr>` elements.
              2. **Initial Column Constraint:** `_initial_column_has_short_text` returns `True`.
              3. **Final Column Numeric & Monotonicity:** `_get_final_column_numeric_values`
                 returns a list of numbers, and `_is_strictly_non_decreasing` on that
                 list returns `True`.
        """
        self.elements_evaluated_count += 1
        rows = table.find_all("tr")

        # 1. Row Count Gate # pyright: ignore[reportUnknownArgumentType]
        if len(rows) < self.context.config.min_tabular_index_rows:
            return False

        # 2. Initial Column Constraint # pyright: ignore[reportUnknownArgumentType]
        if not initial_column_has_short_text(rows, self.context.config.max_chars_in_initial_column):
            return False

        # 3. Final Column Numeric & Monotonicity
        numbers = get_final_column_numeric_values(rows)
        return numbers is not None and is_strictly_non_decreasing(numbers)

    def _purge_tabular_indexes(self, soup: BeautifulSoup) -> None:
        """Finds and purges all tables identified as indexes (Pillar 3).

        Args:
            soup (BeautifulSoup): The in-memory DOM of the document.

        Returns:
            None

        Raises:
            Exception: Per Global Directive #1, any unexpected native exceptions
                will be caught, logged as CRITICAL, and re-raised.

        Mutations:
            - Decomposes `<table>` elements that are certified as indexes.
            - Increments `self.tabular_indexes_purged` and `self.chars_removed_count`.

        Rules & Limits:
            - Traversal: Finds all `<table>` elements in the document.
            - Code Shield: Bypasses any table inside a code block.
            - Full depth traversal: Yes.
        """
        # A static tuple is created to ensure safe iteration while modifying the DOM,
        # as `_purge_nodes` will decompose table tags.
        for table in find_all_snapshot(soup, "table"):
            # Pylance reports a type error because find_all_snapshot returns
            # PageElement, but the called methods expect Tag.
            if not isinstance(table, Tag):
                continue
            if self.context.is_inside_code_block(table):
                continue
            if self._is_potential_tabular_index(table):  # NOSONAR
                self._purge_nodes(soup, [table])
                self.tabular_indexes_purged += 1

    def get_metadata(self, status: PipelineStatus) -> Mapping[str, Any]:
        """Constructs the metadata dictionary for the processing results.

        Args:
            status (PipelineStatus): The final status of the pipeline run.

        Returns:
            dict[str, Any]: A dictionary conforming to the canonical metadata contract.

        Raises:
            None

        Mutations:
            None.

        Rules & Limits:
            - Output Contract: The returned dictionary must be nested under the key
              `navigation_purging` and contain: `nav_elements_purged`,
              `inline_toc_blocks_purged`, `tabular_indexes_purged`,
              `chars_removed_count`, `elements_evaluated_count`, `status`, and
              `execution_timestamp`.
        """
        return generate_processor_metadata(
            processor_key="navigation_purging",
            status=status,
            nav_elements_purged=self.nav_elements_purged,
            inline_toc_blocks_purged=self.inline_toc_blocks_purged,
            tabular_indexes_purged=self.tabular_indexes_purged,
            chars_removed_count=self.chars_removed_count,
            elements_evaluated_count=self.elements_evaluated_count,
        )

    # --- New methods for link density heuristic ---
    def _calculate_link_density(self, tag: Tag) -> float:
        """Calculates the link density of a given tag."""
        total_text_len = len(tag.get_text(strip=True))
        if total_text_len == 0:
            return 0.0

        links = tag.find_all("a")
        link_text_len = sum(len(a.get_text(strip=True)) for a in links)
        return link_text_len / total_text_len

    def _is_navigation_like_element(self, tag: Tag) -> bool:
        """Checks if a tag has navigation-like attributes or classes."""
        if tag.name == "nav" or tag.has_attr("role") and "navigation" in coerce_class_list(tag["role"]):
            return True
        classes = coerce_class_list(tag.get("class"))
        return bool(set(classes).intersection({"menu", "toc"}))

    def _purge_high_link_density_elements(self, soup: BeautifulSoup) -> None:
        """Purges elements based on high link density heuristic."""
        # Use a snapshot to avoid issues with modifying the DOM during iteration
        for tag in find_all_snapshot(soup, ["ul", "div"]):
            if not isinstance(tag, Tag) or self.context.is_inside_code_block(tag):
                continue

            link_density = self._calculate_link_density(tag)

            if tag.name == "ul" and link_density > self.context.config.high_link_density_threshold:
                self._purge_and_log_element(
                    soup, tag, "Purged <ul> with high link density: %s"
                )
            elif (
                tag.name == "div"
                and link_density > self.context.config.high_link_density_threshold
                and self._is_navigation_like_element(tag)
            ):
                self._purge_and_log_element(
                    soup,
                    tag,
                    "Purged <div> with high link density and nav-like properties: %s",
                )

    def _purge_and_log_element(self, soup, tag, message):
        """Purges a node and logs the action."""
        self._purge_nodes(soup, [tag])
        self.nav_elements_purged += 1
        log.debug(message, tag)


register_processor_factory("navigation_purger", NavigationPurger)
