"""A collection of strategies for identifying and processing poetic verse.

This module defines the abstract base class `BasePoetryStrategy` and concrete
implementations for different poetry detection methods, including a parameterized
strategy that reads from a registry and heuristic-based strategies.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

from bs4.element import NavigableString, PageElement, Tag

from ..core import (
    DIALOGUE_DASH_RX,
    SPEAKER_LABEL_RX,
    BookStyleContext,
)
from .indentation_helper import PoetryIndentationHelper


def _get_lines_from_br_tags(target: Tag) -> list[list[PageElement]]:
    """Splits the target's contents by <br> tags, yielding lines.

    Consecutive and trailing ``<br>`` tags are preserved by emitting empty
    lines in the result. This allows downstream consumers to distinguish
    stanza breaks or intentional blank lines from simple intra-line spacing.
    """
    lines: list[list[PageElement]] = []
    current_line: list[PageElement] = []
    for child in target.contents:
        if isinstance(child, Tag) and child.name == "br":
            # End the current line on every <br>, even if empty, so that
            # consecutive or trailing <br> tags become explicit blank lines.
            lines.append(current_line)
            current_line = []
        elif not (isinstance(child, NavigableString) and not child.strip()):
            current_line.append(child)
    # Append the final line if it has content, or if any previous lines were
    # created (which implies a <br> was present). This avoids creating a
    # line from a container with only non-renderable whitespace.
    if lines or current_line:
        lines.append(current_line)
    return lines


class BasePoetryStrategy(ABC):
    """Abstract base class for all poetry identification and normalization strategies."""

    strategy_id: str = "base"

    @abstractmethod
    def can_process(
        self,
        target: Tag,
        context: BookStyleContext,
    ) -> tuple[bool, str | None]:
        """Evaluates if the DOM node matches the poetry signature of this strategy.

        Args:
            target: The DOM node to evaluate.
            context: The shared book style context.

        Returns:
            A tuple: (True if the strategy can process the node, False otherwise,
                      and a string reason if False, None if True).
        """

    @abstractmethod
    def get_lines(
        self,
        target: Tag,
    ) -> Sequence[Tag | list[PageElement]]:
        """Extracts verse lines from a matched target node.

        Args:
            target: The matched poetry container.

        Returns:
            A sequence of lines, where each line can be a Tag or a list of PageElements.
        """


class _HeuristicStrategy(BasePoetryStrategy):
    """A base for heuristic strategies with shared dialogue detection logic."""

    dialogue_exclusion_threshold: float

    def _get_text_from_line(self, line: Tag | list[PageElement]) -> str:
        """Extracts the full text content from a line object.

        The line can be a single Tag or a list of PageElements (typically
        resulting from a split by <br> tags).

        Args:
            line: The line object to process.

        Returns:
            The concatenated text content of the line.
        """
        if isinstance(line, list):
            # A line from <br> splitting is a list of nodes.
            return "".join(
                str(node) if isinstance(node, NavigableString) else node.get_text()
                for node in line
            )
        # A line from paragraph-based strategies is a single Tag.
        return line.get_text()

    def _is_dialogue(self, lines: Sequence[Tag | list[PageElement]]) -> bool:
        """Applies the Dialogue Exclusion Guard."""
        dialogue_count = 0
        line_count = 0
        for line in lines:
            text = self._get_text_from_line(line).strip()
            if not text:
                continue
            line_count += 1
            if DIALOGUE_DASH_RX.match(text) or SPEAKER_LABEL_RX.match(text):
                dialogue_count += 1
        return (
            line_count > 0
            and (dialogue_count / line_count) > self.dialogue_exclusion_threshold
        )


class HeuristicTableStrategy(BasePoetryStrategy):
    """A heuristic strategy to identify poetry formatted within a simple table."""

    strategy_id: str = "heuristic_table"
    MIN_POETIC_TABLE_ROWS: int = 1
    MAX_POETIC_TABLE_COLUMNS: int = 2

    def can_process(
        self,
        target: Tag,
        context: BookStyleContext,
    ) -> tuple[bool, str | None]:
        """Evaluates if the target is a simple table likely containing poetry."""
        if target.name != "table":
            return False, "not_a_table"

        # Reject tables with header cells, as they are strong indicators of data tables.
        if target.find("th"):
            return False, "has_headers"

        # Find rows only in the immediate table body to avoid nested tables.
        row_container = target.find("tbody") or target
        rows = row_container.find_all("tr", recursive=False)
        if len(rows) < self.MIN_POETIC_TABLE_ROWS:
            return False, "not_enough_rows"

        # Since we've already confirmed there are no <th> tags, we only need
        # to count <td> tags per row to check the column constraint.
        if any(
            len(row.find_all("td", recursive=False)) > self.MAX_POETIC_TABLE_COLUMNS
            for row in rows
        ):
            return False, "too_many_columns"
        return True, None

    def get_lines(
        self,
        target: Tag,
    ) -> Sequence[Tag | list[PageElement]]:
        """Extracts lines from the cells of the poetic table.

        Each cell (<td>) in the table is considered a line of verse.
        To avoid capturing content from nested tables, this method only extracts
        `<td>` elements that are direct children of the table's immediate `<tr>`
        rows.
        """
        lines = []
        # Use the same row discovery logic as can_process for consistency.
        row_container = target.find("tbody") or target
        for row in row_container.find_all("tr", recursive=False):
            lines.extend(row.find_all("td", recursive=False))
        return lines


class HeuristicSeparatorStrategy(_HeuristicStrategy):
    """A heuristic strategy to identify poetry based on line separators and text metrics."""

    strategy_id: str = "heuristic_separator"

    def __init__(self, context: BookStyleContext):
        """Initializes the strategy with configuration from the context."""
        self.br_density_threshold = context.config.br_density_threshold
        self.dialogue_exclusion_threshold = context.config.dialogue_exclusion_threshold
        self.enjambment_ratio_threshold = context.config.enjambment_ratio_threshold
        self.max_words_for_enjambment = context.config.poetry_max_words_for_enjambment

    def can_process(
        self,
        target: Tag,
        context: BookStyleContext,
    ) -> tuple[bool, str | None]:
        """Evaluates if the target matches poetry heuristics based on <br> tags."""
        # This strategy is specialized for <br>-based structures.
        if not target.find("br"):
            return False, "no_br_tags"

        candidate_lines = self.get_lines(target)
        if not candidate_lines:
            return False, "no_candidate_lines"

        if self._is_dialogue(candidate_lines):
            return False, "dialogue_excluded"

        line_density, enjambment_ratio = self._calculate_metrics(candidate_lines)
        is_match = (
            line_density is not None and line_density < self.br_density_threshold
        ) or (enjambment_ratio > self.enjambment_ratio_threshold)
        return is_match, None if is_match else "geometric_mismatch"

    def get_lines(
        self,
        target: Tag,
    ) -> Sequence[Tag | list[PageElement]]:
        """Extracts lines from a container by splitting its content by <br> tags."""
        return _get_lines_from_br_tags(target) if target.find("br") else []

    def _calculate_enjambment(self, line_texts: list[str]) -> float:
        """Calculates the enjambment ratio for a list of line texts.

        The enjambment heuristic considers a line "open" when it does not end in
        terminal punctuation. This method assumes it receives a list of pre-filtered
        lines that are guaranteed to contain word characters.

        Lines that exceed `self.max_words_for_enjambment` are ignored for the
        purpose of this ratio, allowing the configuration to control which lines
        participate in the enjambment calculation.
        """
        open_lines = 0
        total_lines = 0
        # As per spec, terminal punctuation does not include closing quotes.
        # We strip closing quotes before checking the last character.
        terminal_punctuation = {".", "!", "?", "…"}
        closing_quote_chars = "\"'”)]}"

        for stripped_text in line_texts:
            # Input `line_texts` are already stripped and confirmed to have content.

            # Skip lines that exceed the configured word-count threshold for enjambment.
            # This wires `max_words_for_enjambment` into the heuristic so that very long
            # lines can be excluded from the ratio, as intended by the configuration.
            if (
                self.max_words_for_enjambment is not None
                and len(stripped_text.split()) > self.max_words_for_enjambment
            ):
                continue

            total_lines += 1

            clean_end_text = stripped_text.rstrip(closing_quote_chars)
            # A line of only quotes would have been filtered out before this method,
            # so `clean_end_text` is guaranteed to not be empty.
            if clean_end_text[-1] not in terminal_punctuation:
                open_lines += 1

        return open_lines / total_lines if total_lines > 0 else 0.0

    def _calculate_metrics(self, lines: Sequence[Any]) -> tuple[float | None, float]:
        """Calculates line density and enjambment ratio for a set of lines."""
        line_texts = [self._get_text_from_line(line) for line in lines]
        # A line is only considered to have content if it contains at least one
        # word character. This prevents punctuation-only lines from being treated
        # as content, which could lead to false positives.
        non_empty_texts = [
            text.strip() for text in line_texts if re.search(r"\w", text)
        ]
        num_lines = len(non_empty_texts)

        if num_lines == 0:
            return None, 0.0

        total_chars = sum(len(text) for text in non_empty_texts)
        line_density = total_chars / num_lines
        enjambment_ratio = self._calculate_enjambment(non_empty_texts)
        return line_density, enjambment_ratio


class HeuristicParagraphContainerStrategy(_HeuristicStrategy):
    """A heuristic strategy for identifying poetry in paragraph-based containers.

    This strategy is designed to catch cases where poetry is structured as
    multiple <p> tags within a container (e.g., <div><p>...</p></div>) or
    when the candidate itself is a <p> tag that is part of a sequence of lines.
    It avoids matching if the primary structure is separator-based (<br> tags).
    """

    strategy_id: str = "heuristic_paragraph_container"

    def __init__(self, context: BookStyleContext):
        """Initializes the strategy with the book style context."""
        self.context = context
        self.dialogue_exclusion_threshold = context.config.dialogue_exclusion_threshold
        # Normalize the word count threshold to ensure a sensible minimum value,
        # guarding against None or zero which could cause overly aggressive rejection.
        max_words = getattr(context.config, "poetry_max_words_for_enjambment", 50)
        self.max_words_for_enjambment = (
            max_words if isinstance(max_words, int) and max_words > 0 else 50
        )
        self.indentation_helper = PoetryIndentationHelper(context)

    def _get_container_and_paragraphs(self, target: Tag) -> list[Tag] | None:
        """Determines the container and finds all direct child paragraphs.

        If the target is a paragraph, its parent is treated as the container to
        analyze its siblings. Otherwise, the target itself is the container.

        Args:
            target: The initial DOM node to analyze.

        Returns:
            A list of paragraph tags to evaluate, or None if no valid structure is found.
        """
        container = target
        if target.name == "p" and target.parent and isinstance(target.parent, Tag):
            container = target.parent

        if child_paragraphs := container.find_all("p", recursive=False):
            return child_paragraphs
        # If the container has no <p> children, but the target itself is a <p>,
        # then we are analyzing a single paragraph with no <p> siblings.
        return [target] if target.name == "p" else None

    def _evaluate_multiple_paragraphs(
        self,
        paragraphs: list[Tag],
    ) -> tuple[bool, str | None]:
        """Evaluates a sequence of multiple paragraphs for poetic structure."""
        if self._is_dialogue(paragraphs):
            return False, "dialogue_excluded"
        # If any paragraph is too long, it's likely prose.
        if any(
            len(p.get_text(strip=True).split()) >= self.max_words_for_enjambment * 2
            for p in paragraphs
        ):
            return False, "paragraph_too_long"
        return True, None

    def _evaluate_single_paragraph(self, p_node: Tag) -> tuple[bool, str | None]:
        """Evaluates a single paragraph for poetic structure."""
        # First, check for definitive rejection reasons for any single line.
        if self._is_dialogue([p_node]):
            return False, "dialogue_excluded"

        if (
            len(p_node.get_text(strip=True).split())
            >= self.max_words_for_enjambment * 2
        ):
            return False, "paragraph_too_long"

        # If not rejected, a single short line is only poetry if it's indented.
        if self.indentation_helper.calculate_indent(p_node) > 0:
            return True, None

        return False, "not_enough_paragraphs"

    def can_process(
        self,
        target: Tag,
        context: BookStyleContext,
    ) -> tuple[bool, str | None]:
        """Checks if the target or its parent is a likely container for paragraph-based poetry,
        and it's not primarily a separator-based pattern.
        """
        # This method is called by StructuralMatcher.match, which then determines
        # the rejection reason if this returns False.

        # This strategy is for paragraph-based structures, not <br>-separated ones.
        if target.find("br"):
            return False, "has_br_tags"

        child_paragraphs = self._get_container_and_paragraphs(target)
        if not child_paragraphs:
            return False, "not_paragraph_container_structure"

        if len(child_paragraphs) > 1:
            return self._evaluate_multiple_paragraphs(child_paragraphs)

        if len(child_paragraphs) == 1:
            return self._evaluate_single_paragraph(child_paragraphs[0])

        # This path should not be reachable.
        return False, "not_paragraph_container_structure"

    def get_lines(self, target: Tag) -> Sequence[Tag | list[PageElement]]:
        """Extracts lines from a paragraph-based container."""
        # Reuse the same container and paragraph discovery logic as `can_process`
        # to ensure that the lines extracted for normalization are the same ones
        # that were validated. This prevents mismatches where `can_process`
        # evaluates a group of siblings but `get_lines` only extracts the
        # original target.
        return self._get_container_and_paragraphs(target) or []
