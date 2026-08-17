"""A multi-strategy engine for footnote and endnote processing.

This package operates as an in-memory DOM manipulation layer. Its sole
responsibility is to reorder, isolate, type, and standardize the hierarchical
tree of footnotes and endnotes using a cascade of static and data-parameterized
strategies. It ensures that all structural mutations result in a valid
BeautifulSoup tree, without injecting any raw Markdown syntax.

Analytical Blueprint:
---------------------

Based on the specification, the following logic will be mapped to the class
methods:

Global Free Functions (Module Level):
    - None present in the skeleton.

Class Methods:
    - BaseFootnoteStrategy:
        - can_process: Abstract method to evaluate if the DOM matches the strategy's signature.
        - process: Abstract method to execute the in-place DOM mutation and return results.
    - ParameterizedFootnoteStrategy:
        - __init__: Initializes the strategy from a configuration dictionary, extracting `callout_regex`,
        `body_selector`, `backlink_selector`, and `body_topology_location`.
        - can_process: Checks if `soup.select(self.body_selector)` finds any elements.
        - process: Executes the note processing loop using the configured selectors and returns the mutated soup and metadata.
    - FootnoteProcessor:
        - __init__: Initializes telemetry counters (`notes_count`, `anomalies_detected`) and state.
        - process: Orchestrates the strategy selection cascade in strict priority order:
          1. Stage 0 (Native Convention)
          2. Stage A (Known Static Strategies, e.g., AriaDpubStrategy)
          3. Stage B (Parametric Registry Search)
          4. Stage C (Anomaly Containment)
          5. Stage D (Forensic Triage)
          It executes the first strategy for which `can_process()` returns `True` and returns the result.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from bs4 import BeautifulSoup

from ..core import (
    BookStyleContext,
    EngineConfiguration,
    PipelineStatus,
)
from ..core.component_registry import register_processor_factory
from .strategies import (
    AnomalyStrategy,
    AriaDpubStrategy,
    BaseFootnoteStrategy,
    ParameterizedFootnoteStrategy,
)
from .strategies.base_strategy import FootnoteStrategyError

if TYPE_CHECKING:
    from ..core import BookStyleContext

log = logging.getLogger(__name__)


@register_processor_factory("footnotes")
def create_footnote_processor(
    context: BookStyleContext,
    **kwargs: Any,
) -> FootnoteProcessor:
    """Factory function to create a FootnoteProcessor instance with its strategies."""
    strategies: list[BaseFootnoteStrategy] = [
        AriaDpubStrategy(),
    ]
    patterns = getattr(context.config, "footnote_patterns", [])
    strategies.extend(
        ParameterizedFootnoteStrategy(config_params=pattern) for pattern in patterns
    )
    strategies.append(AnomalyStrategy())
    return FootnoteProcessor(context, strategies=strategies)


class FootnoteProcessor:
    """
    The main orchestration engine for footnote and endnote processing.

    This class manages the entire footnote normalization pipeline. It initializes
    a prioritized cascade of different `BaseFootnoteStrategy` implementations,
    including static strategies for known standards (like `AriaDpubStrategy`),
    data-driven strategies for registered patterns (`ParameterizedFootnoteStrategy`),
    and fallback strategies for handling anomalies (`AnomalyStrategy`).

    When its `process` method is called, it iterates through the strategy
    cascade, executing the first strategy that reports it can handle the given
    DOM structure. This ensures a predictable, ordered, and extensible approach
    to footnote processing.
    """

    # --- Metadata Keys ---
    _KEY_STRATEGY = "strategy_applied"
    _KEY_NOTES_FOUND = "notes_found_count"
    _KEY_NOTES_REBUILT = "notes_rebuilt_count"
    _KEY_BACKLINKS_INJECTED = "backlinks_injected_count"
    _KEY_ANOMALIES_REPAIRED = "anomalies_repaired_count"

    def __init__(
        self,
        context: BookStyleContext,
        strategies: Sequence[BaseFootnoteStrategy],
    ) -> None:
        """Initializes the footnote processor, its state, and the strategy cascade.

        Args:
            context (BookStyleContext): The shared context for the book, providing
                access to the engine configuration.
            strategies (Sequence[BaseFootnoteStrategy]): The ordered cascade of
                strategies to apply.

        Returns:
            None

        Raises:
            None

        Mutations:
            - Initializes telemetry counters and state variables.
            - Initializes `self.strategies` with the provided cascade of footnote
              processing strategies.

        Rules & Limits:
            - Instance Lifecycle: Assumes this instance is scoped to a single book.
            - Strategy Cascade: The list of strategies is injected to ensure
              Inversion of Control.
        """
        self.context = context
        self.config: EngineConfiguration = context.config
        self.strategy_applied: str = "unrecognized"
        self.notes_found: int = 0
        self.notes_rebuilt: int = 0
        self.backlinks_injected: int = 0
        self.anomalies_repaired: int = 0
        self.strategies: Sequence[BaseFootnoteStrategy] = strategies
        for strategy in self.strategies:
            strategy.processor = self

    def process(
        self,
        soup: BeautifulSoup,
        all_soups: dict[str, BeautifulSoup] | None = None,
    ) -> tuple[BeautifulSoup, dict[str, Any]]:
        """Orchestrates the footnote processing by executing the strategy cascade.

        This method iterates through the pre-initialized strategy cascade stored
        in `self.strategies`, selecting and executing the first one that can process
        the given DOM. It also updates the processor's internal state with the
        results from the applied strategy.

        Args:
            soup (BeautifulSoup): The DOM tree to process.
            all_soups (dict[str, BeautifulSoup] | None): A dictionary mapping all
                file keys to their soup objects, for cross-file strategies.

        Returns:
            tuple[BeautifulSoup, dict[str, Any]]: A tuple containing the mutated
                soup and a metadata dictionary from the applied strategy.

        Raises:
            Exception: Per Global Directive #1, any unexpected native exceptions
                will be caught, logged as CRITICAL, and re-raised.

        Mutations:
            - The input `soup` object is mutated in-place by the selected strategy.
            - Updates `self.strategy_applied`, `self.notes_count`, and
              `self.anomalies_detected` with the results from the applied strategy.

        Rules & Limits:
            - Strategy Cascade: The method executes the strategy cascade defined
              in `self.strategies`. The order of this cascade is determined at
              initialization.
            - Selection Logic: The first strategy in the cascade for which
              `can_process()` returns `True` is selected and executed. The loop
              terminates after the first successful strategy application.
            - Full depth traversal: Yes.

        Calls:
            - `can_process`: On each strategy to determine applicability.
            - `process`: On the first applicable strategy to execute it.
        """
        for strategy in self.strategies:
            try:
                if result := self._apply_single_strategy(strategy, soup, all_soups):
                    return result
            except FootnoteStrategyError:
                # Known, recoverable strategy-specific errors (e.g., config issues)
                log.exception(
                    "Footnote strategy '%s' encountered a recoverable error",
                    strategy.__class__.__name__,
                )
                continue  # Continue to next strategy
            except Exception:  
                # Unexpected critical errors in strategy execution
                log.critical(
                    "Unexpected critical error in footnote strategy '%s'",
                    strategy.__class__.__name__,
                    exc_info=True,
                )
                # Pass-Through Guard Clause: log and continue to next strategy
                continue

        log.info(
            "No applicable footnote strategy found for context: %s",
            self._get_context_identifier(),
        )
        self.strategy_applied = "none"
        return (
            soup,
            BaseFootnoteStrategy.create_metadata(
                strategy_name="none",
                status=PipelineStatus.SUCCESS_NOOP,  # Changed notes_count to notes_processed_count
                notes_processed_count=0,
            ),
        )

    def _apply_single_strategy(
        self,
        strategy: BaseFootnoteStrategy,
        soup: BeautifulSoup,
        all_soups: dict[str, BeautifulSoup] | None,
    ) -> tuple[BeautifulSoup, dict[str, Any]] | None:
        """Applies a single strategy to the soup if it is applicable.

        This helper encapsulates the logic for checking, executing, and updating
        telemetry for a single strategy.

        Args:
            strategy: The footnote strategy instance to apply.
            soup: The DOM tree to process.
            all_soups: A dictionary of all soup objects in the book.

        Returns:
            A tuple of the mutated soup and metadata if the strategy was
            applied, otherwise None.
        """
        if not strategy.can_process(soup, self.context):
            return None

        log.info("Applying footnote strategy: %s", strategy.__class__.__name__)
        mutated_soup, metadata = strategy.process(soup, self.context, all_soups)

        # Update processor state from the strategy's metadata.
        if results := metadata.get("footnote_processing"):
            self.strategy_applied = results.get(self._KEY_STRATEGY, "unknown")
            self.notes_found += results.get(self._KEY_NOTES_FOUND, 0)
            self.notes_rebuilt += results.get(self._KEY_NOTES_REBUILT, 0)
            self.backlinks_injected += results.get(self._KEY_BACKLINKS_INJECTED, 0)
            self.anomalies_repaired += results.get(self._KEY_ANOMALIES_REPAIRED, 0)

        return mutated_soup, metadata

    def _get_context_identifier(self) -> str:
        """Resolves a human-friendly identifier from the context for logging."""
        # Chain of getattr calls to find the first available identifier.
        identifier = (
            getattr(self.context, "identifier", None)
            or getattr(self.context, "book_id", None)
            or getattr(self.context, "file_key", None)
        )
        # Fallback to the class name if no specific identifier is found.
        return str(identifier) if identifier else self.context.__class__.__name__
