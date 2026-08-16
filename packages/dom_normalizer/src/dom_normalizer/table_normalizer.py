"""A forensic reconstruction and relational consolidation engine for tables.

This module operates as a Stage 2 processor. Its objective is to intercept
visual scaffolding (div-based grids, preformatted text) or fragmented native
tables and mutate them into semantic, continuous XHTML tables. This ensures
that tabular data is correctly interpreted by downstream systems.

This processor must run after `heading_normalizer` and strictly before
`list_normalizer` to prevent misidentification of data matrices.

Analytical Blueprint:
---------------------

Based on the specification, the following logic will be mapped to the class
methods:

Global Free Functions (Module Level):
    - None present in the skeleton.

Class Methods (TableNormalizer):
    - __init__: Initializes telemetry counters for the three cases:
      `div_tables_reconstructed`, `spacer_tables_reconstructed`, `fused_tables_count`.
    - process: Orchestrates the three-layer normalization pipeline in strict
      order: 1. `_extract_spacer_tables` (Case C), 2. `_reconstruct_div_grids`
      (Case A), 3. `_fuse_fragmented_tables` (Case B).
    - _extract_spacer_tables: Implements Case C. Finds `<p>` and `<pre>` tags,
      delegates line parsing to `tokenize_spacer_line`, and if a tabular
      signature is found (>=3 columns), reconstructs the node into a `<table>`.
    - _get_tokenized_lines_if_table: Helper for Case C. Checks if a node contains
      at least one line with >= 3 columns after tokenization.
    - _create_table_from_tokens: Helper for Case C. Performs the DOM mutation,
      creating a `<table>` and mapping the first line to `<th>` cells. -
    - _reconstruct_div_grids: Implements Case A. Finds `<div>` grids and delegates
      the entire mutation to the internal helper `_safe_convert_div_grid_to_table`.
    - _fuse_fragmented_tables: Implements Case B. Finds all `<table>` tags and
      attempts to merge each with its next valid sibling table.
    - _try_fuse_with_next, _find_next_sibling_table, _are_tables_fusable,
      _perform_fusion, _count_table_columns: These are all helper methods for
      the Case B fusion logic, implementing the column-count and header checks,
      noise bypass (using `is_ignorable_node`), and final DOM mutation. The
      `_reconstruct_div_grids` method is now deprecated and its logic is
      subsumed by `_recover_div_tables`.
"""

import logging
from collections.abc import Mapping
from typing import Any

from bs4 import BeautifulSoup, Tag
from bs4.element import PageElement

from .core import BookStyleContext, PipelineStatus
from .core.dom_utils import (
    find_all_snapshot,
    generate_processor_metadata,
    is_ignorable_node,
)

log = logging.getLogger(__name__)


class TableNormalizer:
    """A forensic reconstruction and relational consolidation engine for tables.

    This processor operates in three distinct layers to heal table structures:
    1.  **Spacer Table Extraction (Case C):** Reconstructs tables from
        preformatted text blocks (`<p>`, `<pre>`) that use multiple spaces or
        tabs to align columns.
    2.  **Div Grid Reconstruction (Case A):** Converts `<div>`-based grid
        layouts that visually mimic tables into semantic `<table>` elements.
    3.  **Fragmented Table Fusion (Case B):** Merges adjacent, structurally
        compatible `<table>` elements that are separated only by ignorable
        noise, creating a single, continuous table.

    The processor is designed to be robust against DOM mutations during
    iteration and ensures that all transformations adhere to the project's
    semantic and structural contracts.
    """

    MIN_DIV_TABLE_ROWS: int = 2
    MIN_DIV_TABLE_COLS: int = 2
    HEADER_PROMOTION_THRESHOLD: float = 0.5
    MIN_TABLES_FOR_FUSION: int = 2

    def __init__(self, context: BookStyleContext) -> None:
        """Initializes the table normalizer with context and telemetry.

        Args:
            context (BookStyleContext): The shared context for the book.

        Returns:
            None

        Raises:
            None

        Mutations:
            - Initializes `self.context` to the provided context object.
            - Initializes `self.tables_recovered` to 0.
            - Initializes `self.tables_repaired` to 0.

        Rules & Limits:
            - Instance Lifecycle: Assumes this instance is scoped to a single book,
              per Global Directive #3.
        """
        self.context = context
        self.tables_recovered: int = 0
        self.tables_repaired: int = 0

    def process(self, soup: BeautifulSoup) -> tuple[BeautifulSoup, Mapping[str, Any]]:
        """Executes the full three-layer table normalization pipeline.

        This is the main entry point. It orchestrates the reconstruction of
        tables from preformatted text and div grids, and then fuses fragmented
        tables.

        Args:
            soup (BeautifulSoup): The in-memory DOM of the document to be processed.

        Returns:
            tuple[BeautifulSoup, dict[str, Any]]: A tuple containing the mutated soup
                object and a dictionary with metadata about the normalization process.

        Raises:
            Exception: Per Global Directive #1, any unexpected native exceptions
                during processing will be caught, logged as CRITICAL, and re-raised.

        Mutations:
            - The input `soup` object is modified in-place by the various layer
              methods.

        Rules & Limits:
            - Internal Layer Execution Order: The layers MUST be executed in this
              strict sequence: 1. `_recover_div_tables`, 2. `_recover_orphan_trs`,
              3. `_repair_native_tables`, 4. `_fuse_fragmented_tables`.
            - Pipeline Order Contract: This processor must run after
              `heading_normalizer`
              and before `list_normalizer`.
            - Full depth traversal: Yes.
            - Status Logic: Returns 'success' if any tables were reconstructed or
              fused. Otherwise, returns 'idle'.
        """
        try:
            self._recover_div_tables(soup)
            self._recover_orphan_trs(soup)
            self._repair_native_tables(soup)
            self._fuse_fragmented_tables(soup)
        except Exception:
            log.critical(
                "TableNormalizer failed with an unhandled exception.",
                exc_info=True,
            )
            raise

        has_changes = self.tables_recovered > 0 or self.tables_repaired > 0
        status = PipelineStatus.SUCCESS if has_changes else PipelineStatus.SUCCESS_NOOP

        return soup, generate_processor_metadata(
            processor_key="table_normalization",
            status=status,
            tables_recovered=self.tables_recovered,
            tables_repaired=self.tables_repaired,
        )

    def _recover_div_tables(self, soup: BeautifulSoup) -> None:
        """Recovers tables from div-based grid structures."""
        for container in find_all_snapshot(soup, "div", class_="table"):
            if not isinstance(
                container,
                Tag,
            ) or self.context.is_inside_literal_code_tag(
                container,
            ):
                continue

            rows = container.find_all("div", class_="row", recursive=False)
            if len(rows) < self.MIN_DIV_TABLE_ROWS:
                continue

            first_row_cells = rows[0].find_all("div", class_="cell", recursive=False)
            if len(first_row_cells) < self.MIN_DIV_TABLE_COLS:
                continue

            new_table = soup.new_tag("table")
            thead = soup.new_tag("thead")
            tbody = soup.new_tag("tbody")
            new_table.extend([thead, tbody])

            header_tr = soup.new_tag("tr")
            for cell_div in first_row_cells:
                th = soup.new_tag("th")
                th.string = cell_div.get_text(strip=True)
                header_tr.append(th)
            thead.append(header_tr)

            for row_div in rows[1:]:
                body_tr = soup.new_tag("tr")
                for cell_div in row_div.find_all("div", class_="cell", recursive=False):
                    td = soup.new_tag("td")
                    td.string = cell_div.get_text(strip=True)
                    body_tr.append(td)
                tbody.append(body_tr)

            container.replace_with(new_table)
            self.tables_recovered += 1

    def _recover_orphan_trs(self, soup: BeautifulSoup) -> None:
        """Wraps orphan <tr> elements in a proper table structure."""
        valid_table_parents = {"tbody", "thead", "tfoot", "table"}
        # Only wrap orphan <tr> tags found in common block-level containers.
        # This prevents mutating valid, non-tabular layouts that might use <tr>
        # for custom components (e.g., inside <template> or other elements).
        allowed_orphan_contexts = {"body", "div", "section", "article", "main"}
        for tr_tag in find_all_snapshot(soup, "tr"):
            if not isinstance(tr_tag, Tag) or self.context.is_inside_literal_code_tag(
                tr_tag,
            ):
                continue

            parent = tr_tag.parent
            if not parent:
                continue

            # If the parent is a valid table part, it's not an orphan.
            if parent.name in valid_table_parents:
                continue

            # If the parent is a safe context for an orphan, wrap it.
            if parent.name in allowed_orphan_contexts:
                table = soup.new_tag("table")
                tbody = soup.new_tag("tbody")
                table.append(tbody)
                tr_tag.wrap(tbody)
                tbody.wrap(table)
                self.tables_recovered += 1

    def _is_header_row(self, cells: list[Tag]) -> bool:
        """Determines if a row should be promoted to a header based on bold cells.

        Args:
            cells: The list of cells in the row.

        Returns:
            True if the row meets the criteria for a header, False otherwise.
        """
        # If there are no cells, it can't be a header row.
        if not cells:
            return False

        # Default promotion for rows without any bolding, as per the test
        # INJECT_THEAD_TBODY_DEFAULT.
        if not any(cell.find("b") or cell.find("strong") for cell in cells):
            return True

        bold_cells = sum(bool(cell.find("b") or cell.find("strong")) for cell in cells)
        promotion_ratio = bold_cells / len(cells)
        return promotion_ratio > self.HEADER_PROMOTION_THRESHOLD

    def _promote_to_header(self, row: Tag, table: Tag, soup: BeautifulSoup) -> None:
        """Promotes a table row to a <thead>, converting cells to <th>.

        Args:
            row: The row to promote.
            table: The parent table.
            soup: The BeautifulSoup instance.
        """
        thead = soup.new_tag("thead")
        table.insert(0, thead)
        thead.append(row.extract())
        for cell in row.find_all("td"):
            cell.name = "th"
            for bold_tag in cell.find_all(["b", "strong"]):
                bold_tag.unwrap()

    def _restructure_table_body(
        self,
        table: Tag,
        rows: list[Tag],
        soup: BeautifulSoup,
    ) -> None:
        """Restructures a table by adding thead/tbody and promoting headers.

        This method checks if the first row should be a header, promotes it if
        necessary, and wraps all remaining body rows in a <tbody> tag.

        Args:
            table: The table to restructure.
            rows: The list of rows in the table.
            soup: The BeautifulSoup instance.
        """
        first_row = rows[0]
        cells = first_row.find_all(["td", "th"])

        if cells and self._is_header_row(cells):
            self._promote_to_header(first_row, table, soup)

        if remaining_rows := table.find_all("tr", recursive=False):
            tbody = soup.new_tag("tbody")
            # Insert tbody after thead if it exists, otherwise at the beginning
            if thead := table.find("thead"):
                thead.insert_after(tbody)
            else:
                table.insert(0, tbody)

            for row in remaining_rows:
                tbody.append(row.extract())

    def _repair_native_tables(self, soup: BeautifulSoup) -> None:
        """Injects missing <thead>/<tbody> and promotes headers."""
        for table in find_all_snapshot(soup, "table"):
            if not isinstance(table, Tag) or self.context.is_inside_literal_code_tag(
                table,
            ):
                continue

            # Skip tables that already have a proper structure
            if table.find("thead"):
                continue

            # Find rows, which might be in a parser-injected tbody
            tbody = table.find("tbody")
            row_container = tbody or table
            rows = row_container.find_all("tr", recursive=False)

            if not rows:
                continue

            # If a tbody was found, it was likely inserted by the parser.
            # We unwrap it to get a clean slate of <tr> elements directly
            # under the <table>, which _restructure_table_body expects.
            if tbody:
                tbody.unwrap()

            # Re-fetch the rows now that they are direct children of the table.
            clean_rows = table.find_all("tr", recursive=False)

            # If we are here, the table will be repaired.
            self._restructure_table_body(table, clean_rows, soup)
            self.tables_repaired += 1

    def _perform_one_fusion_pass(self, soup: BeautifulSoup) -> bool:
        """
        Scans the document for a single pair of adjacent, fusable tables and
        merges them.

        This function performs one pass over all tables. It's designed to be
        called repeatedly until no more fusions can be made in an entire pass.
        The first valid pair found is fused, and the function returns immediately.

        Args:
            soup: The BeautifulSoup object representing the document.

        Returns:
            True if a fusion was performed, False otherwise.

        Raises:
            None

        Mutations:
            - May trigger a fusion via `_try_fuse_with_next`, which modifies the DOM.
        """
        tables = find_all_snapshot(soup, "table")
        if len(tables) < self.MIN_TABLES_FOR_FUSION:
            return False

        for table_a in tables:
            # Skip tables that have been detached or are inside code blocks
            if (
                not isinstance(table_a, Tag)
                or table_a.parent is None
                or self.context.is_inside_literal_code_tag(
                    table_a,
                )
            ):
                continue

            if self._try_fuse_with_next(table_a):
                return True  # A fusion was made, so the pass was successful.

        return False  # No fusions were made in this pass.

    def _fuse_fragmented_tables(self, soup: BeautifulSoup) -> None:
        """Layer 3: Finds and fuses fragmented, adjacent tables (Case B).

        This method orchestrates the fusion of adjacent tables by repeatedly
        scanning the document. In each pass, it attempts to find and merge a
        single pair of compatible tables. This process continues until a full
        pass over the document results in no fusions, ensuring all possible
        fragmented tables are consolidated.

        Args:
            soup (BeautifulSoup): The in-memory DOM of the document.

        Returns:
            None

        Raises:
            None

        Mutations:
            - Repeatedly calls `_perform_one_fusion_pass` which modifies the DOM.
        """
        while self._perform_one_fusion_pass(soup):
            self.tables_repaired += 1

    def _try_fuse_with_next(self, table_a: Tag) -> bool:
        """Attempts to fuse a given table with its next valid sibling table.

        This method orchestrates the fusion logic for a single table by finding a
        potential partner, validating fusibility, and performing the merge.

        Args:
            table_a (Tag): The starting `<table>` tag.

        Returns:
            bool: `True` if a fusion occurred, `False` otherwise.

        Raises:
            None

        Mutations:
            - May trigger a fusion via `_perform_fusion`.

        Rules & Limits:
            - Sibling Contiguity Guard: Fusion operates exclusively on direct,
              un-wrapped sibling `<table>` nodes, separated only by ignorable noise.
        """
        noise_elements, table_b = self._find_next_sibling_table(table_a)
        if table_b and self._are_tables_fusable(table_a, table_b):
            self._perform_fusion(table_a, table_b, noise_elements)
            log.debug("Fused two adjacent tables.")
            return True
        return False

    def _find_next_sibling_table(
        self,
        start_node: Tag,
    ) -> tuple[list[PageElement], Tag | None]:
        """Scans for the next sibling `<table>`, collecting intermediate noise.

        Args:
            start_node (Tag): The node from which to start scanning siblings.

        Returns:
            tuple[list[PageElement], Tag | None]: A tuple containing a list of the
                intermediate noise elements and the found sibling `<table>` tag
                (or `None` if no suitable table is found).

        Raises:
            None

        Mutations:
            None.

        Rules & Limits:
            - Delegation Contract: Each intermediate sibling node MUST be evaluated
              using `is_ignorable_node(node)`. If it returns `True`, the node is
              collected as noise.
            - Scan Termination: The scan stops immediately if a non-noise,
              non-table element is encountered.
        """
        noise_elements: list[PageElement] = []
        current_node = start_node.next_sibling

        while current_node:
            # Delegate primary decision to is_ignorable_node
            if is_ignorable_node(current_node):
                noise_elements.append(current_node)
                current_node = current_node.next_sibling
                continue

            # If we encounter a table tag, we've found the next candidate
            if isinstance(current_node, Tag) and current_node.name == "table":
                return noise_elements, current_node

            # For non-Tag nodes (e.g., NavigableString), allow certain benign
            # content to be treated as ignorable even if is_ignorable_node
            # did not classify them as such (to avoid premature termination).
            if not isinstance(current_node, Tag):
                text = str(current_node).strip()
                if not text:
                    # Treat empty/whitespace-only text as noise
                    noise_elements.append(current_node)
                    current_node = current_node.next_sibling
                    continue
                # Non-empty, non-Tag content is considered a hard boundary
                break

            # Any non-table Tag that is not classified as ignorable is a hard
            # boundary and terminates the scan.
            break

        # If we exit the loop without finding a table, return collected noise
        # but indicate that there is no subsequent fusable table.
        return noise_elements, None

    def _are_tables_fusable(self, table_a: Tag, table_b: Tag) -> bool:
        """Checks if two tables can be legally fused based on structural rules.

        Args:
            table_a (Tag): The first table.
            table_b (Tag): The second, subsequent table.

        Returns:
            bool: `True` if the tables are fusable, `False` otherwise.

        Raises:
            None

        Mutations:
            None.

        Rules & Limits:
            - Fusion is permitted if and only if all of the following are true:
              1. Neither table contains cells with `colspan` or `rowspan`.
              2. `table_b` contains no `<th>` header cells.
              3. The column count of `table_a` is equal to the column count of `table_b`.
        """
        # Reject fusion if any cell in either table uses colspan or rowspan.
        if table_a.find(
            lambda tag: (
                tag.name in ("td", "th")
                and (tag.has_attr("colspan") or tag.has_attr("rowspan"))
            ),
        ) or table_b.find(
            lambda tag: (
                tag.name in ("td", "th")
                and (tag.has_attr("colspan") or tag.has_attr("rowspan"))
            ),
        ):
            return False

        if table_b.find("th"):
            return False

        cols_a = self._count_table_columns(table_a)
        cols_b = self._count_table_columns(table_b)

        return cols_a != 0 and cols_a == cols_b

    def _perform_fusion(
        self,
        table_a: Tag,
        table_b: Tag,
        noise_elements: list[PageElement],
    ) -> None:
        """Executes the DOM mutation to fuse two tables and remove noise.

        Args:
            table_a (Tag): The primary table to which rows will be appended.
            table_b (Tag): The secondary table whose rows will be moved.
            noise_elements (list[PageElement]): A list of intermediate nodes to
                be removed.

        Returns:
            None

        Raises:
            None

        Mutations:
            - Moves all `<tr>` elements from `table_b`'s `<tbody>` to `table_a`'s `<tbody>`.
            - Decomposes all `noise_elements` from the DOM.
            - Decomposes the now-empty `table_b` from the DOM.
            - Increments `self.fused_tables_count`.
        """
        # Get the body of table A, or the table itself if no body exists.
        tbody_a = table_a.find("tbody") or table_a

        # and extract all direct child rows from it.
        row_container_b = table_b.find("tbody") or table_b
        rows_to_move = row_container_b.find_all("tr", recursive=False)

        # Move the rows to table A and clean up.
        tbody_a.extend(rows_to_move)

        for noise in noise_elements:
            noise.decompose()
        table_b.decompose()

    def _count_table_columns(self, table: Tag) -> int:
        """Counts the number of columns in the first row of a table.

        Args:
            table (Tag): The `<table>` to inspect.

        Returns:
            int: The number of `<td>` and `<th>` cells in the first `<tr>`, or 0
                if the table has no rows.

        Raises:
            None

        Mutations:
            None.

        Rules & Limits:
            - The count is based solely on the first `<tr>` element found.
            - Node Type Safety: Handles cases where a table might not have a `<tbody>`
              or `<tr>` by returning 0.
        """
        first_row = table.find("tr")
        return len(first_row.find_all(["td", "th"])) if first_row else 0
