"""A collection of utility functions for navigation purging logic.

This module centralizes regexes and numeric parsing helpers used by the
`NavigationPurger` to make the matching logic easier to audit and adjust.
"""

import re
from collections.abc import Sequence

from bs4 import Tag

from .config import EngineConfiguration

# Regex for file-based fallback (Pillar 1)
FILE_FALLBACK_RX: re.Pattern[str] = re.compile(
    r"/(nav|toc|indice|contents|summary)\.xhtml$",
    re.IGNORECASE,
)


def get_toc_line_rx(config: EngineConfiguration) -> re.Pattern[str]:
    """Generates a compiled regex for inline TOC lines based on configuration."""
    return re.compile(
        rf"^.{{{config.min_toc_line_chars},{config.max_toc_line_chars}}}?(?:[.-]{{2,}}|\s+)\d+(?:\D.*)?$",
        re.DOTALL,
    )


# --- Pillar 2 Helpers ---


def extract_trailing_numbers_from_block(block: Sequence[Tag]) -> list[int] | None:
    """Parses the trailing integer from the text of each node in a block.

    Raises:
        None

    Mutations:
        None

    Args:
        block (Sequence[Tag]): A list of nodes identified as a potential TOC block.

    Returns:
        list[int] | None: A list of the extracted trailing integers, or `None`
            if any node in the block does not have a trailing integer.
    """
    numbers = []
    for node in block:
        # Strip trailing whitespace, then find a number at the very end of the line.
        # SonarLint warning: Simplify this regular expression to reduce its runtime,
        # as it has super-linear performance due to backtracking.
        # Original: if match := re.search(r"\d+$", text):
        # Alternative to avoid potential backtracking issues with greedy quantifiers
        # and end-of-string anchor, by reversing the string and using re.match.
        text = node.get_text().rstrip()
        reversed_text = text[::-1]
        if match := re.match(r"\d+", reversed_text):
            numbers.append(int(match[0][::-1]))  # Reverse the matched digits back
        else:
            # If any line lacks a trailing number, it's not a valid checklist.
            return None
    return numbers


def is_arithmetic_progression(
    numbers: list[int],
    min_lines: int,
    config: EngineConfiguration,
) -> bool:
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
    if len(numbers) < min_lines or numbers[0] not in config.checklist_start_numbers:
        return False
    return all(numbers[i] - numbers[i - 1] == 1 for i in range(1, len(numbers)))


# --- Pillar 3 Helpers ---


def get_final_column_numeric_values(rows: Sequence[Tag]) -> list[int] | None:
    r"""Extracts the first contiguous block of digits from the last cell of each row in a table.

    Args:
        rows (Sequence[Tag]): A list of `<tr>` tags from a `<table>`.

    Returns:
        list[int] | None: A list of the extracted integers, or `None` if any
            final cell lacks a numeric digit.

    Rules & Limits:
        - Extraction: For each row, finds the last `<td>` or `<th>`.
        - Validation: If any final cell contains text but lacks any numeric
          digit, the entire process aborts and returns `None`.
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
            # This case should ideally not happen in a valid table row,
            # but we handle it defensively.
            return None

        last_cell = cells[-1]
        cell_text = last_cell.get_text().strip()

        # If the cell is empty, it's not a valid page number.
        if not cell_text:
            return None

        if match := re.search(r"\d+", cell_text):
            values.append(int(match[0]))
        else:
            # Contains something but not a number, or no number found.
            return None
    return values


def is_strictly_non_decreasing(numbers: list[int]) -> bool:
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


def initial_column_has_short_text(rows: Sequence[Tag], max_chars: int) -> bool:
    """Implements the "Initial Column Constraint" for Pillar 3.

    Checks if the first cell of every row in a table has a short text label.

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
        if not first_cell:
            # Skip malformed rows, or consider it a failure if a row is expected
            # to have a first cell. For this check, we assume malformed rows
            # don't contribute to the "short text" property.
            continue
        if len(first_cell.get_text(strip=True)) >= max_chars:
            return False
    return True
