"""Identifies poetic verses using statistical analysis of line lengths."""

from __future__ import annotations

import contextlib
import logging
import re
import statistics

from bs4 import BeautifulSoup, Tag

from ..core import BookStyleContext
from ..core.dom_utils import normalize_style_attribute
from .base_strategy import PROCESSOR_UNBOUND_MSG, BaseBlockquoteStrategy

log = logging.getLogger(__name__)


class PoeticQuoteStrategy(BaseBlockquoteStrategy):
    """Identifies poetic verses using statistical analysis of line lengths.

    This is the second-priority strategy (Priority 2). It analyzes sequences of
    sibling paragraphs to detect patterns typical of poetry, such as short lines
    with low variance in length. It is designed to distinguish verse from prose.
    """

    def find_and_apply(
        self,
        start_node: Tag,
        context: BookStyleContext,
        soup: BeautifulSoup,
    ) -> list[Tag] | None:
        """Finds and applies the poetic quote strategy (Priority 2).

        This method attempts to identify a poetic quote starting at `start_node`
        using statistical analysis of line lengths. If a valid sequence is found,
        it is wrapped in a `<blockquote>` and the list of processed nodes is
        returned.

        Mutations:
            - Modifies the DOM in-place by wrapping the identified poetic nodes
              in a new `<blockquote>` element.

        Rules & Limits:
            - This is the second priority strategy (Priority 2).
            - Full depth traversal: Yes.
        """
        if (
            sequence := self._collect_sequence(start_node, context)
        ) and self._is_candidate_valid(sequence):
            self._wrap_nodes_in_blockquote(sequence, soup)
            assert self.processor, PROCESSOR_UNBOUND_MSG
            self.processor.generic_quotes_created_count += 1
            return sequence
        return None

    def _is_candidate_valid(self, nodes: list[Tag]) -> bool:
        """Applies validation filters suitable for poetry, skipping the TTR check.

        This override bypasses the Text-to-Tag Ratio (TTR) filter from the
        base class, which is too aggressive for short-lined poetic verse. It
        retains the anchor density filter to prevent navigation menus from being
        misidentified as poetry by reusing the base implementation.

        Args:
            nodes: A list of candidate `Tag` objects forming a potential
                blockquote.

        Returns:
            True if the candidate passes the anchor density filter, False otherwise.
        """
        if not nodes:
            return False

        # We cannot call super()._is_candidate_valid() because we need to skip
        # the TTR check. Instead, we call the specific validation helpers we need.
        stats = self._get_content_stats(nodes)

        return self._is_anchor_density_valid(
            stats["anchor_chars"],
            stats["total_chars"],
        )

    def _is_valid_poetic_paragraph(
        self,
        node: Tag | None,
        context: BookStyleContext,
    ) -> bool:
        """Checks if a node is a valid paragraph for a poetic sequence.

        A node is valid if it's a `<p>` tag, not already in a blockquote, and
        not styled like an indented prose quote (which would be handled by
        `ProseQuoteStrategy`).

        Args:
            node: The node to check.
            context: The book's style context.

        Returns:
            True if the node is a valid part of a potential poetic sequence.
        """
        if not (
            isinstance(node, Tag)
            and node.name == "p"
            and not node.find_parent("blockquote")
        ):
            return False

        # Defer to ProseQuoteStrategy (Priority 3) if the node has an explicit
        # indent style. This check is crucial for isolated tests where the
        # structural sanitizer hasn't run.
        if node.has_attr("style"):
            style_str = normalize_style_attribute(node.get("style"))
            if self._has_indent_style(style_str):
                log.debug(
                    "PoeticQuoteStrategy: Node has indent style; deferring to ProseQuoteStrategy.",
                )
                return False

        # Defer if it has been marked as a blockquote element by a prior process
        # (the primary mechanism in the full pipeline).
        return not context.is_blockquote_element(node)

    def _has_indent_style(self, style_str: str) -> bool:
        """Heuristically determines if a style string indicates left indentation.

        This is a conservative check to defer to `ProseQuoteStrategy`. It covers:
        - Explicit `margin-left` / `padding-left` declarations.
        - `text-indent` declarations.
        - Basic `margin` / `padding` shorthand with a non-zero left value.

        Args:
            style_str: A normalized inline style string.

        Returns:
            True if an indentation style is detected, False otherwise.
        """
        # Check for explicit left margin/padding or text-indent.
        # A non-zero value is not checked here; any declaration is enough to defer.
        if re.search(
            r"(?:(?:margin|padding)-left|text-indent)\s*:",
            style_str,
            re.IGNORECASE,
        ):
            return True

        # Basic shorthand parsing for margin/padding.
        shorthand_match = re.search(
            r"\b(margin|padding)\s*:\s*([^;]+)",
            style_str,
            re.IGNORECASE,
        )
        if not shorthand_match:
            return False

        values = shorthand_match[2].strip()
        parts = re.split(r"\s+", values)

        # Determine the 'left' value from shorthand.
        if len(parts) == 1:
            left = parts[0]
        elif len(parts) in {2, 3}:
            left = parts[1]
        elif len(parts) >= 4:
            left = parts[3]
        else:  # 0 parts, should not happen with the regex
            return False

        # Treat any non-zero left value as indentation.
        with contextlib.suppress(ValueError, IndexError):
            numeric_part = re.match(r"^\s*([+-]?\d*\.?\d+)", left)
            if numeric_part and float(numeric_part[1]) != 0:
                return True
        return False

    def _find_sequence_start(
        self,
        start_node: Tag,
        context: BookStyleContext,
    ) -> Tag:
        """Traverses backwards from a node to find the start of a poetic sequence.

        This ensures that if the processor starts in the middle of a poem,
        it finds the beginning and processes the whole poem.

        Args:
            start_node: The node to start traversing from.
            context: The book's style context.

        Returns:
            The first valid poetic paragraph tag in the sequence.
        """
        first_node_in_sequence = start_node
        current = start_node
        while True:
            prev_sibling_candidate = self._get_prev_non_ignorable_sibling(current)
            # Explicitly check if it's a Tag and a valid poetic paragraph.
            if isinstance(
                prev_sibling_candidate,
                Tag,
            ) and self._is_valid_poetic_paragraph(prev_sibling_candidate, context):
                first_node_in_sequence = prev_sibling_candidate
                current = prev_sibling_candidate
            else:
                break
        return first_node_in_sequence

    def _collect_from_start(
        self,
        start_node: Tag,
        context: BookStyleContext,
    ) -> list[Tag]:
        """Collects a poetic sequence forwards from a given start node.

        Args:
            start_node: The node to start collecting from.
            context: The book's style context.

        Returns:
            A list of tags forming the poetic sequence.
        """
        sequence = []
        current = start_node
        while current and self._is_valid_poetic_paragraph(current, context):
            sequence.append(current)
            current = self._get_next_non_ignorable_sibling(current)
        return sequence

    def _collect_sequence(
        self,
        start_node: Tag,
        context: BookStyleContext,
    ) -> list[Tag] | None:
        """Collects a sequence of sibling paragraph-like tags that resemble a poem.

        This strategy uses statistical properties of text line lengths to identify
        poetry, which typically consists of short, consistently-lengthed lines.

        Rules & Limits:
            - Structural Invariant: This strategy operates exclusively on sequences
              of independent, sibling `<p>` elements. It does not
              process poetry formatted with `<br>` tags.
            - Statistical Heuristics: Detects poetic verses by analyzing
              sequences of sibling tags. It matches if the mean character length
              is <= `MAX_POETIC_MEAN_LENGTH` and the variance is low (σ² <=
              `MAX_POETIC_VARIANCE`).
            - Sibling Traversal: The method safely traverses `previous_sibling`
              and `next_sibling` results, checking that they are valid `<p>` tags.
        """
        if not self._is_valid_poetic_paragraph(start_node, context):
            # If the node is otherwise a valid paragraph but has an indent, it's
            # a prose candidate. Log this specific case for better debugging.
            # The start_node is already typed as a Tag, so the isinstance check is redundant.
            if context.is_blockquote_element(start_node):
                log.debug(
                    "PoeticQuoteStrategy: Node is marked as a 'blockquote-element', deferring to ProseQuoteStrategy.",
                )
            return None

        first_node = self._find_sequence_start(start_node, context)
        sequence = self._collect_from_start(first_node, context)

        # After collecting the full sequence, apply statistical validation.
        raw_line_texts = [p.get_text(strip=True) for p in sequence]

        # Filter out empty or near-empty lines before computing statistics so that
        # structural blank lines do not bias the mean/variance toward a "poetic" shape.
        assert self.config is not None, "Config not bound to strategy"
        line_texts = [
            text for text in raw_line_texts if len(text) >= self.config.poetic_quote_min_content_line_length
        ]

        # If filtering removes too many lines, treat the sequence as non-poetic.
        if len(line_texts) < self.config.poetic_quote_min_lines:
            return None

        return sequence if self._meets_statistical_criteria(line_texts) else None

    def _meets_statistical_criteria(self, line_texts: list[str]) -> bool:
        """Checks if a sequence of nodes meets the statistical criteria for poetry.

        Args:
            line_texts: A list of stripped text content from candidate nodes.

        Returns:
            True if the sequence has a short mean line length and low variance,
            False otherwise.
        """
        assert self.config is not None, "Config not bound to strategy"
        if len(line_texts) < self.config.poetic_quote_min_lines:
            return False

        line_lengths = [len(text) for text in line_texts]
        mean_length = statistics.mean(line_lengths)
        # Use population variance as it's more intuitive for this kind of
        # heuristic and matches the test case expectations.
        variance = statistics.pvariance(line_lengths) if len(line_lengths) > 1 else 0.0

        return (
            mean_length <= self.config.poetic_quote_max_mean_length
            and variance <= self.config.poetic_quote_max_variance
        )
