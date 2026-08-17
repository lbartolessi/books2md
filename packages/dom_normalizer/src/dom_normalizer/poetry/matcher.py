"""A read-only observer that determines if a DOM fragment is poetry.

This module contains the `StructuralMatcher` class, which is responsible for
analyzing a DOM node against a cascade of strategies to determine if it
represents poetic verse. It operates in a read-only capacity and provides
detailed match results or rejection reasons.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from bs4.element import Tag

from ..core import BookStyleContext
from .strategies import (
    BasePoetryStrategy,
    HeuristicParagraphContainerStrategy,
    HeuristicSeparatorStrategy,
    HeuristicTableStrategy,
)

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class MatchResult:
    """Represents the result of a poetry structural match analysis."""

    match_type: str
    strategy_id: str | None
    matching_mode: str | None
    rejection_reason: str | None
    node_to_process: Tag | None = None


class StructuralMatcher:
    """A read-only observer that finds a matching poetry strategy for a DOM fragment."""

    def __init__(self, context: BookStyleContext):
        """Initializes the matcher with configuration from the context.

        This constructor resolves configurations, thresholds, and paths directly
        from the context's EngineConfiguration to enforce clean Inversion of
        Control (IoC).

        Args:
            context (BookStyleContext): The shared context for the book, providing
                access to configuration.

        Returns:
            None

        Raises:
            None

        Mutations:
           - Sets `self.context`.
            - Sets `self.registry_path`, `self.br_density_threshold`,
              `self.dialogue_exclusion_threshold`, `self.enjambment_ratio_threshold`,
              and `self.max_words_for_enjambment` from `context.config`.
            - Initializes `self.strategies` to an empty list.

        Rules & Limits:
            - Instance Lifecycle: Assumes this instance is scoped to a single book.
        """
        self.context = context
        self.heuristic_table_strategy = HeuristicTableStrategy(context)
        self.heuristic_separator_strategy = HeuristicSeparatorStrategy(context)
        self.heuristic_paragraph_container_strategy = (
            HeuristicParagraphContainerStrategy(context)
        )

    def get_strategy_by_id(self, strategy_id: str) -> BasePoetryStrategy | None:
        """Retrieves a strategy instance by its unique ID.

        Args:
            strategy_id: The unique identifier of the strategy to retrieve.

        Returns:
            The strategy instance if found, otherwise None.
        """
        if strategy_id == self.heuristic_table_strategy.strategy_id:
            return self.heuristic_table_strategy
        if strategy_id == self.heuristic_separator_strategy.strategy_id:
            return self.heuristic_separator_strategy
        if strategy_id == self.heuristic_paragraph_container_strategy.strategy_id:
            return self.heuristic_paragraph_container_strategy

        return None

    def _get_rejection_payload(
        self,
        mode: str,
        reason: str,
    ) -> MatchResult | None:
        """Determines if a rejection is definitive and returns the payload.

        Some rejection reasons from strategies mean the candidate is simply not
        applicable for that strategy (e.g., a non-table for the table strategy),
        and the matcher should continue to the next strategy. Other reasons are
        definitive rejections of a valid candidate (e.g., a table that is too
        wide), and the matcher should stop and report the failure.

        Args:
            mode: The matching mode being attempted (e.g., "table", "separator").
            reason: The rejection reason string from the strategy.

        Returns:
            A MatchResult object for a definitive rejection, or None to continue.
        """
        rejection_reason_for_telemetry: str | None = None

        if reason == "dialogue_excluded":
            rejection_reason_for_telemetry = "dialogue_excluded"
        elif (
            (mode == "table" and reason != "not_a_table")
            or (mode == "separator" and reason == "geometric_mismatch")
            or (mode == "container" and reason == "paragraph_too_long")
        ):
            rejection_reason_for_telemetry = "geometric_mismatch"

        if rejection_reason_for_telemetry:
            return MatchResult(
                match_type="none",
                strategy_id=None,
                matching_mode=mode,
                rejection_reason=rejection_reason_for_telemetry,
                node_to_process=None,
            )
        return None

    def match(self, target: Tag) -> MatchResult:
        r"""Analyzes a target tag against geometric and registry-based traits.

        This is a read-only observer that finds the first strategy that can process
        the given DOM fragment. It checks parameterized strategies from the registry
        first, then falls back to heuristic-based strategies.

        Args:
            target (Tag): The DOM node to analyze. Must be a `bs4.Tag`.

        Returns:
            MatchResult: An object detailing the match result.

        Raises:
            Exception: Per Global Directive #1, any unexpected native exceptions
                during processing will be caught, logged as CRITICAL, and re-raised.

        Mutations:
            None.

        Strategy Cascade:
            1.  **Heuristic Table Strategy:**
                it attempts to match a poetic table structure.
            2.  **Heuristic Separator Strategy:** It applies
                geometric and textual analysis to detect poetry in sequences of
                `<p>` or `<br>` separated lines. This includes the Dialogue
                Exclusion Guard.
            3.  **Heuristic Paragraph Container Strategy:** It applies
                geometric and textual analysis to detect poetry in sequences of
                `<p>` tags within a container.
        """
        try:
            # --- Layer 1: Heuristic Table Strategy ---
            # This strategy is highly specific and expects a <table> node. We check if the
            # target is a simple container for a single table.
            child_tables = target.find_all("table", recursive=False)
            other_tags = [
                t for t in target.find_all(True, recursive=False) if t.name != "table"
            ]
            if len(child_tables) == 1 and not other_tags:
                table_node = child_tables[0]
                is_match, reason = self.heuristic_table_strategy.can_process(
                    table_node,
                    self.context,
                )
                if is_match:
                    return MatchResult(
                        match_type="structural",
                        strategy_id=self.heuristic_table_strategy.strategy_id,
                        matching_mode="table",
                        rejection_reason=None,
                        node_to_process=table_node,
                    )
                if reason and (
                    rejection_payload := self._get_rejection_payload("table", reason)
                ):
                    return rejection_payload

            # --- Layer 2 & 3: Separator and Paragraph Container Strategies ---
            # These strategies can operate on a container (like the target itself)
            # or a single child element within it.
            content_children = [
                child for child in target.contents if isinstance(child, Tag)
            ]
            node_to_test = content_children[0] if len(content_children) == 1 else target

            strategies_to_try = [
                (self.heuristic_separator_strategy, "separator"),
                (self.heuristic_paragraph_container_strategy, "container"),
            ]
            for strategy, mode in strategies_to_try:
                is_match, reason = strategy.can_process(node_to_test, self.context)
                if is_match:
                    return MatchResult(
                        match_type="structural",
                        strategy_id=strategy.strategy_id,
                        matching_mode=mode,
                        rejection_reason=None,
                        node_to_process=node_to_test,
                    )
                if reason and (
                    rejection_payload := self._get_rejection_payload(mode, reason)
                ):
                    return rejection_payload

            # If no strategy produced a match or a definitive rejection, fail.
            return MatchResult(
                match_type="none",
                strategy_id=None,
                matching_mode=None,
                rejection_reason=None,
                node_to_process=None,
            )
        except Exception:
            log.critical(
                "StructuralMatcher failed with an unhandled exception on target: <%s>",
                target.name,
                exc_info=True,
            )
            raise
