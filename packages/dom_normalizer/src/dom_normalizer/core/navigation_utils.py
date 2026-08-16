"""A collection of utility functions for navigation purging logic.

This module centralizes regexes and numeric parsing helpers used by the
`NavigationPurger` to make the matching logic easier to audit and adjust.
"""

import re
from collections.abc import Sequence

from bs4 import Tag

# Regex for file-based fallback (Pillar 1)
FILE_FALLBACK_RX: re.Pattern[str] = re.compile(
    r"/(nav|toc|indice|contents|summary)\.xhtml$",
    re.IGNORECASE,
)

# Regex for inline TOC line pattern (Pillar 2)
TOC_LINE_RX: re.Pattern[str] = re.compile(
    # A more efficient regex to avoid catastrophic backtracking.
    # It matches two or more dots/hyphens, or one or more spaces.
    # The end part `(?:\D.*)?` ensures that after matching digits, the next
    # character must be a non-digit, preventing backtracking issues with `\d+.*`.
    r"^.{3,70}?(?:[.-]{2,}|\s+)\d+(?:\D.*)?$",
    re.DOTALL,
)

# --- Pillar 2 Helpers ---


def _extract_trailing_numbers(block: Sequence[Tag]) -> list[int] | None:
    """Extracts the trailing integer from each node's text in a block.

    Raises:
        None

    Mutations:
        None

    Args:
        block (Sequence[Tag]): A list of nodes identified as a potential TOC block.
    """
    numbers = []
    for node in block:
        # Strip trailing whitespace, then find a number at the very end of the line.
        text = node.get_text().rstrip()
        # SonarLint warning: Simplify this regular expression to reduce its runtime,
        # as it has super-linear performance due to backtracking.
        # To avoid potential ReDoS from `\d+$`, we reverse the string and use
        # `re.match`, which is anchored at the beginning and more efficient.
        reversed_text = text[::-1]
        if match := re.match(r"\d+", reversed_text):
            # Reverse the matched digits back to their original order and convert to int.
            numbers.append(int(match[0][::-1]))
        else:
            # If any line lacks a trailing number, it's not a valid checklist.
            return None
    return numbers


def _is_arithmetic_progression(numbers: list[int], min_lines: int) -> bool:
    """Implements the "Agnostic Anti-Step Guard" for Pillar 2.

    This checks if a sequence of numbers is a simple arithmetic progression
    starting at 0 or 1, which indicates an instruction list rather than a TOC.

    Args:
        numbers (list[int]): A list of integers extracted from a block.
        min_lines (int): The minimum number of lines required for a block to be
            considered a potential inline TOC.

    Returns:
        bool: `True` if the list is a simple arithmetic progression to be
            preserved, `False` otherwise.

    Raises:
        None

    Mutations:
        None

    Rules & Limits:
        - A sequence is preserved if it is an arithmetic progression increasing
          by exactly +1, starting from either 0 or 1 (e.g., `[1, 2, 3, 4]`).
    """
    if len(numbers) < min_lines or numbers[0] not in (0, 1):
        return False
    return all(numbers[i] - numbers[i - 1] == 1 for i in range(1, len(numbers)))


def _extract_final_column_numbers(rows: Sequence[Tag]) -> list[int]:
    r"""Extracts the first contiguous block of digits from the last cell of each row in a table.

    This function is designed to be resilient, skipping rows that are malformed
    or do not contain a numeric value in their final cell, rather than aborting
    the entire extraction.

    Args:
        rows (Sequence[Tag]): A list of `<tr>` tags from a `<table>`.

    Returns:
        list[int]: A list of the extracted integers. This list may be empty if
            no rows contain valid numeric values.

    Rules & Limits:
        - Extraction: For each row, finds the last `<td>` or `<th>`.
        - Validation: Skips any row that is malformed (no cells), has an empty
          last cell, or whose last cell does not contain any numeric digits.
        - Parsing: Extracts the first contiguous block of digits (`\d+`) found
          in the cell's text, ignoring any leading sign or formatting characters
          (e.g., "-", "+", ",", ".").

    Raises:
        None
    """
    values = []
    for row in rows:
        cells = row.find_all(["td", "th"], recursive=False)
        if not cells:
            # Defensively skip malformed rows rather than aborting.
            continue

        last_cell = cells[-1]
        cell_text = last_cell.get_text().strip()

        # If the cell is empty, it's not a valid page number; skip this row.
        if not cell_text:
            continue

        if match := re.search(r"\d+", cell_text):
            values.append(int(match[0]))
        else:
            # Contains something but not a number, or no number found; skip this row.
            continue
    return values


def _is_non_decreasing(numbers: list[int]) -> bool:
    """Implements the "Strict Monotonicity Rule" for Pillar 3.

    Checks if a list of numbers is in a non-decreasing monotonic progression.

    Args:
        numbers (list[int]): The list of page numbers from a table's final column.

    Returns:
        bool: `True` if `p_i <= p_{i+1}` for all `i`, `False` otherwise.

    Rules & Limits:
        - No Approximations: Approximate match ratios, percentage-based
          thresholds, or error tolerances are strictly prohibited.

    Raises:
        None

    Mutations:
        None
    """
    return all(numbers[i] <= numbers[i + 1] for i in range(len(numbers) - 1))


def _first_column_has_short_text(rows: Sequence[Tag], max_chars: int) -> bool:
    """Implements the "Initial Column Constraint" for Pillar 3.

    Checks if the first cell of every table row has a short text label.

    Args:
        rows (Sequence[Tag]): A list of `<tr>` tags from a `<table>`.
        max_chars (int): The maximum character length for the text in the first
            cell of a table row.

    Returns:
        bool: `True` if all first cells meet the length constraint, `False`
            if any single row exceeds the limit.

    Rules & Limits:
        - Length Constraint: For every row, the stripped text length of the
          first `<td>` or `<th>` must be strictly less than `max_chars`.

    Raises:
        None

    Mutations:
        None
    """
    for row in rows:
        first_cell = row.find(["td", "th"], recursive=False)
        if not first_cell:  # Malformed row, skip it.
            # Malformed rows (those without a first cell) are skipped and do not
            # affect the constraint, as they are not valid TOC rows.
            continue
        if len(first_cell.get_text(strip=True)) >= max_chars:
            return False
    return True
