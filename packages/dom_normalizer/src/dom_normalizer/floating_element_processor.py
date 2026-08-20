"""An isolation barrier for non-linear layout components like sidebars.

This module identifies and mutates floating layout elements (e.g., sidebars,
callouts, marginal notes) into semantic `<aside>` tags. This is a critical
step for downstream RAG models, as it prevents narrative contamination and
token duplication by semantically isolating auxiliary content from the primary
text flow.

This processor operates as the third and final step in Stage 1, executing
after `structural_sanitizer` and `navigation_purger`.

Analytical Blueprint:
---------------------

Based on the specification, the following logic will be mapped to the class
methods:

Global Free Functions (Module Level):
    - None present in the skeleton.

Class Methods (FloatingElementProcessor):
    - __init__: Initializes telemetry counters (`asides_created`,
      `containment_guard_rejections`, `density_guard_rejections`, `elements_evaluated`).
    - process: Orchestrates the main processing loop. It performs a one-time
      text extraction to cache the document's character count for efficient
      density calculations. It then finds all potential floating elements and
      subjects each to a 5-step guard framework. If a node is approved, it's
      transformed into an `<aside>`. Finally, it compiles and returns the
      execution metadata.
    - _is_candidate_for_transformation: Acts as the master gatekeeper, calling
      the other helper methods in sequence to apply the 5-step guard framework.
      It aborts if the node is inside a code block, is a dense structural
      container, or fails the density check.
    - _is_dense_container: Implements the "Containment Guard" (Step 3). It
      returns `True` if a node contains major structural tags (from config) or
      more than one major heading tag (from config), preventing primary content
      from being mutated.
    - _get_density_threshold: Selects the appropriate density cap (standard or
      enhanced) based on the node's metadata.
    - _passes_density_guard: Implements the "Density Cap" logic (Steps 4 & 5).
      It exempts nodes with fewer than 50 characters. For larger nodes, it
      calculates the Character Density Ratio (CDR) and compares it against the
      dynamic threshold provided by `_get_density_threshold`.
    - _transform_node_to_aside: Performs the in-place DOM mutation. It creates a
      new `<aside>` tag, preserves only the `id` attribute from the original
      node, moves all children into the new `<aside>`, and replaces the
      original node in the DOM.
    - get_metadata: Compiles the final metadata dictionary using the instance
      counters and returns it in the specified format.
"""

from __future__ import annotations

import logging
from typing import Any

from bs4 import BeautifulSoup, Tag

from .core import BookStyleContext, PipelineStatus
from .core.component_registry import register_processor_factory
from .core.config import EngineConfiguration
from .core.dom_utils import (
    coerce_class_list,
    get_tag_identifier,
    get_utc_timestamp,
    is_ignorable_node,
    select_snapshot,
)

log = logging.getLogger(__name__)


class FloatingElementProcessor:
    """Isolates non-linear layout components like sidebars into <aside> tags."""

    def __init__(self, context: BookStyleContext) -> None:
        """Initializes the semantic isolation engine.

        This constructor sets up the processor with the shared book context and
        initializes all telemetry counters to zero.

        Args:
            context: Core class managing style heuristics and global configurations.

        Mutations:
            - Sets `self.context`.
            - Initializes all telemetry counters to 0.
            - Initializes `self._total_document_chars` to 0.
            - Initializes `self._layout_indicator_classes` to None.

        Rules & Limits:
            - Caching Contract: `_total_document_chars` is cached once per `process` call.
            - Instance Lifecycle: Assumes this instance is scoped to a single book,
              per Global Directive #3.

        """
        self.context = context
        self.config: EngineConfiguration = context.config
        self.asides_created: int = 0
        self.elements_evaluated: int = 0
        self.containment_guard_rejections: int = 0
        self.density_guard_rejections: int = 0
        # One-time cache to avoid O(n^2) complexity in density checks.
        self._total_document_chars: int = 0
        # Lazily-loaded cache for all layout indicator classes.
        self._layout_indicator_classes: set[str] | None = None

    def process(self, soup: BeautifulSoup) -> tuple[BeautifulSoup, dict[str, Any]]:
        """Finds and transforms all floating elements into semantic <aside> tags.

        This is the main entry point. It first performs a one-time text extraction
        of the entire document to cache its character count for efficient density
        calculations. It then iterates through all potential floating elements,
        subjecting each to a rigorous 5-step guard framework to identify legitimate
        floating content. Approved nodes are mutated into `<aside>` elements.

        Args:
            soup: The in-memory DOM of the document to be processed.

        Returns:
            A tuple containing the mutated soup object and a dictionary with
            metadata about the normalization process.

        Mutations:
            - The input `soup` object is modified in-place by `_transform_node_to_aside`
              for each node that passes the validation checks.

        Rules & Limits:
            - Traversal: The processor must find and evaluate all `Tag` elements in the
              document.
            - Dependency: This processor relies on the `structural_sanitizer` having
              already promoted inline `float` styles to the `floating-element` class.
            - Full depth traversal: Yes.
        """
        body = soup.body
        if not body:
            log.warning("No <body> tag found; skipping floating element processing.")
            return soup, self.get_metadata(PipelineStatus.SKIPPED)

        # One-time cache to avoid O(n^2) complexity in density checks.
        # Use soup.body to avoid including <head> content in the total, which
        # could skew the density ratio.
        self._total_document_chars = len(body.get_text())

        # Short-circuit for very small or empty documents to avoid misleading ratios.
        if self._total_document_chars < self.config.min_document_chars_for_processing:
            log.debug(
                "Skipping floating element processing: document too short (%d chars).",
                self.config.min_document_chars_for_processing,
            )
            return soup, self.get_metadata(PipelineStatus.SKIPPED)

        # Build a selector for all known floating compounds to pre-filter candidates.
        selectors = [
            "." + ".".join(sorted(compound))
            for compound in self.context.floating_compounds
            if compound
        ]

        if not selectors:
            return soup, self.get_metadata(PipelineStatus.SUCCESS_NOOP)

        css_selector = ", ".join(selectors)

        # `soup.select()` returns a list of unique tags, robustly handling
        # selectors with multiple classes regardless of their order in the
        # attribute. This automatically de-duplicates nodes that match multiple
        # parts of the compound selector. We convert the result to a tuple to
        # create a static snapshot, ensuring safe iteration while the DOM is being
        # modified.
        for node in select_snapshot(soup, css_selector):
            if not isinstance(node, Tag):
                continue
            if self._is_candidate_for_transformation(node):
                self._transform_node_to_aside(node, soup)

        status = (
            PipelineStatus.SUCCESS
            if self.asides_created > 0
            else PipelineStatus.SUCCESS_NOOP
        )
        return soup, self.get_metadata(status)

    def _is_candidate_for_transformation(self, node: Tag) -> bool:
        """Applies the 5-step operational guard framework to a candidate node.

        This method acts as the master gatekeeper, determining if a node is a valid
        target for transformation. It sequentially applies all verification steps,
        from code immunity to density checks.

        Args:
            node: The DOM node to evaluate. Must be a `bs4.Tag`.

        Returns:
            True if the node passes all guards and should be transformed into
            an `<aside>`, False otherwise.

        Rules & Limits:
            - Execution Order (Guard Framework):
              1. **Code Block Shield:** Aborts if `self.context.is_inside_code_block(node)` is `True`.
              2. **Molecular Identity:** The `process` loop's selector pre-filters candidates, so this step is implicit.
              3. **Containment Guard:** Aborts if `self._is_dense_container(node)` is `True`.
              4. **Density Guard:** Aborts if `self._passes_density_guard(node)` is `False`.

        Mutations:
            - Increments `self.elements_evaluated`.
            - Increments `self.containment_guard_rejections` or `self.density_guard_rejections`
              if the respective guard fails.

        """
        # Step 1: Code Block Shield
        if self.context.is_inside_code_block(node):
            return False

        # Step 2: Molecular Identity (pre-filtered by the `process` loop's selector)
        self.elements_evaluated += 1

        # Step 3: Containment Guard
        if self._is_dense_container(node):
            self.containment_guard_rejections += 1
            return self._reject_candidate(
                "Node rejected by containment guard (is dense)",
                node,
            )
        # Steps 4 & 5: Density Guard
        if not self._passes_density_guard(node):
            self.density_guard_rejections += 1
            return self._reject_candidate(
                "Node rejected by density guard",
                node,
            )
        return True

    def _reject_candidate(self, reason: str, node: Tag) -> bool:
        """Logs the reason for a candidate's rejection.

        This is a helper to centralize the logging for nodes that are preserved
        because they fail one of the validation guards.

        Args:
            reason (str): The reason for the rejection.
            node (Tag): The node that was rejected.

        Returns:
            bool: Always returns False to signal rejection.
        """
        log.debug("%s: %s", reason, self._get_node_summary(node))
        return False

    def _get_node_summary(self, node: Tag) -> str:
        """Creates a concise summary of a tag for logging purposes.

        Args:
            node (Tag): The tag to summarize.

        Returns:
            str: A string summary of the tag, including its name, id, and class.
        """
        return get_tag_identifier(node, self.config.tag_identifier_attr_value_limit)

    @property
    def layout_indicator_classes(self) -> set[str]:
        """Lazily computes and caches the set of all layout indicator classes.

        An "indicator" class provides extra layout hints (e.g., 'sidebar') for an
        element already identified as floating by a "base" class. This logic
        infers "base" classes as the *union* of all classes found within the
        "simplest" floating compounds (those with the fewest classes). "Layout
        indicator" classes are then defined as any classes present in *any*
        floating compound that are *not* part of these inferred "base" classes.

        Heuristics & Assumptions:
            - This property relies on the heuristic that the "base" identity of a
              floating element is defined by the class(es) in the smallest
              compounds. For example, if the configured compounds are
              `{frozenset({'float'}), frozenset({'float', 'sidebar'})}`, the
              smallest compound is `{'float'}`, which is inferred as the base
              identity.
            - Any classes that appear only in larger compounds (like 'sidebar'
              in this example) are treated as "indicator" classes that provide
              additional layout hints. This model is robust for many common CSS
              patterns but assumes that base identity classes are not exclusively
              found in larger, more complex compounds.

        Returns:
            set[str]: A set of all unique class names from the floating compounds
                configuration that are considered layout indicators.
        """
        if self._layout_indicator_classes is None:
            # Materialize the compounds to prevent issues with one-shot iterators.
            all_compounds = tuple(self.context.floating_compounds)
            if not all_compounds:
                self._layout_indicator_classes = set()
                return self._layout_indicator_classes

            # Filter out empty compounds to handle potentially malformed configurations.
            non_empty_compounds = [c for c in all_compounds if c]
            if not non_empty_compounds:
                self._layout_indicator_classes = set()
                return self._layout_indicator_classes

            # Find the size of the smallest "base" compound.
            min_compound_size = min(len(c) for c in non_empty_compounds)

            # Base classes are any classes that appear in a compound of minimum size.
            # These are considered the fundamental identity classes for floating elements.
            base_classes = {
                klass
                for compound in non_empty_compounds
                if len(compound) == min_compound_size
                for klass in compound
            }

            # All classes from all compounds.
            all_classes = {
                klass for compound in non_empty_compounds for klass in compound
            }

            # Layout indicators are any classes that are NOT part of the base identity.
            # For example, if compounds are {frozenset({'float'}), frozenset({'float', 'sidebar'})},
            # min_size is 1, base_classes is {'float'}, and the indicator is {'sidebar'}.
            self._layout_indicator_classes = all_classes - base_classes
            log.debug(
                "Computed layout classes from %d compounds. Base: %s, Indicators: %s",
                len(non_empty_compounds),
                sorted(base_classes),
                sorted(self._layout_indicator_classes),
            )
        return self._layout_indicator_classes

    def _is_dense_container(self, node: Tag) -> bool:
        """Implements the Containment Guard (Step 3) to protect macro-content.

        This check prevents the processor from accidentally transforming major
        structural sections of the document that might happen to have floating
        properties.

        Args:
            node: The candidate node to inspect. Must be a `bs4.Tag`.

        Returns:
            True if the node is considered a dense, primary content container,
            False otherwise.

        Mutations:
            None.

        Rules & Limits:
            - A node is considered a dense container if either:
                - Its own tag (`node.name`) is a major structural tag (e.g., `<body>`).
                - Its subtree contains any of those major structural tags.
                - Its own tag (`node.name`) is a major heading tag (e.g., `<h1>`).
                - Its subtree contains more than one major heading tag.
            - Node Type Safety: Expects a `Tag`. A `NavigableString` will not have
              children and will correctly result in a `False` return.
            - Full depth traversal: Yes, within the scope of the `node`.
        """
        # Check if the node itself is a major structural tag defined in the configuration
        # or if such a tag exists within its descendants.
        if node.name in self.context.config.dense_container_tags or node.find(
            self.context.config.dense_container_tags,
        ):
            return True

        # Check if the node itself is a major heading tag defined in the configuration.
        if node.name in self.context.config.dense_container_heading_tags:
            return True

        # Check if more than one such heading exists within its descendants.
        # Using limit=2 is a performance optimization: find_all stops after finding 2.
        return (
            len(
                node.find_all(
                    self.context.config.dense_container_heading_tags,
                    limit=2,
                ),
            )
            > 1
        )

    def _get_density_threshold(self, node: Tag) -> float:
        """Selects the appropriate density cap based on node metadata.

        Args:
            node (Tag): The node to evaluate.

        Returns:
            The density threshold for the node.
        """
        # The presence of `data-orig-bg` is a heuristic indicating that the
        # element was styled with a background color, a common technique for
        # visual callouts or sidebars. This justifies a higher density threshold.
        node_classes = coerce_class_list(node.get("class"))
        has_layout_class = any(k in self.layout_indicator_classes for k in node_classes)
        if (
            node.get("data-meta-layout") == "true"
            or node.get("data-orig-bgcolor")
            or has_layout_class
        ): # pyright: ignore[reportUnknownArgumentType]
            return self.config.layout_enhanced_density_cap
        return self.config.standard_density_cap

    def _passes_density_guard(self, node: Tag) -> bool:
        """Implements the density cap logic (Steps 4 & 5).

        This method evaluates a node's character density to distinguish between # pyright: ignore[reportUnusedMethod]
        small, auxiliary sidebars and large, primary content blocks. It uses an
        absolute length exemption for very short nodes and a dynamic relative
        threshold for all others.

        Args:
            node: The candidate node to evaluate. Must be a `bs4.Tag`.

        Returns:
            True if the node is within the allowed density limits, False otherwise.

        Mutations:
            None.

        Rules & Limits:
            - **Empty Node Guard:** If the node's stripped text is empty, it is
              rejected.
            - **Absolute Length Exemption:** If the node's character count is less than
              or equal to `DENSITY_EXEMPTION_CHAR_THRESHOLD`, it is approved.
            - **Dynamic Cap Allocation:**
                - **Layout Enhanced Cap:** Used if the node has a `data-meta-layout="true"`
                  attribute, a `data-orig-bgcolor` attribute, or a class from the
                  `layout_indicator_classes` set.
                - **Standard Cap:** Used for all other cases.
            - **Threshold Validation:**
                - The Character Density Ratio (CDR) is calculated as:
                  `CDR = node_chars / self._total_document_chars`.
                - Returns `True` if `CDR <= threshold`.
            - **Zero Division Guard:** If `_total_document_chars` is zero, the node
              is rejected to prevent division by zero errors.
        """
        # Per the specification, the density is calculated based on the node's
        # total character footprint, including all descendants. This provides a
        # simple, predictable measure of the content being isolated.
        node_text = node.get_text()
        if not node_text.strip():
            # Per review, empty or whitespace-only containers are not candidates
            # for transformation into an <aside>.
            return False
        node_chars = len(node_text)

        # Step 4: Absolute Length Exemption
        if node_chars <= self.config.density_exemption_char_threshold:
            return True

        # Step 4: Dynamic Cap Allocation
        threshold = self._get_density_threshold(node)

        # Step 5: Threshold Validation
        if self._total_document_chars == 0:
            # Given the earlier short-circuit when `_total_document_chars`
            # is below `MIN_DOCUMENT_CHARS_FOR_PROCESSING`, reaching zero here
            # suggests an internal inconsistency. We fail-soft by rejecting the
            # node while emitting telemetry for investigation.
            log.warning(
                "FloatingElementProcessor density validation anomaly: "
                "_total_document_chars is 0 during density validation; rejecting node. "
                "node_chars=%d, node_summary=%s",
                node_chars,
                self._get_node_summary(node),
            )
            return False

        cdr = node_chars / self._total_document_chars
        return cdr <= threshold

    def _transform_node_to_aside(self, node: Tag, soup: BeautifulSoup) -> None:
        """Performs the in-place mutation of a validated node into an <aside>.

        This method executes the final transformation. It creates a new `<aside>`
        element, preserves the `id` attribute if present, and migrates the
        original node's content. It adheres to the "Zero-Class Annihilation
        Contract" by stripping all other attributes and all classes.

        Args:
            node: The validated `Tag` object to be transformed.
            soup: The root `BeautifulSoup` object, used as a factory
                for creating the new `<aside>` element.

        Mutations:
            - Creates a new `<aside>` tag.
            - Preserves the `id` attribute from the original node, if it exists.
            - Strips all other attributes, including `class` and `style`.
            - Moves all children from `node` into the new `<aside>` tag.
            - Replaces `node` with the new `<aside>` tag in the DOM tree.
            - Increments `self.asides_created`.

        Rules & Limits:
            - **Attribute Preservation:** Only the `id` attribute is preserved.
            - **Zero-Class Policy:** The new `<aside>` tag will have no `class` attribute.
        """
        parent = node.parent
        if not parent:
            log.warning(
                "Cannot transform node to <aside> because it has no parent: %s",
                self._get_node_summary(node),
            )
            return

        aside_tag = soup.new_tag("aside")

        # Per spec v2.14 (Zero-Class Annihilation Contract), only preserve the 'id'.
        if node_id := node.get("id"):
            aside_tag["id"] = node_id

        # Per review, determine if the parent <p> should be replaced BEFORE
        # mutating the node's contents, as this check depends on the node's
        # context within its parent.
        should_replace_parent_p = parent.name == "p" and all(
            is_ignorable_node(c, self.config) for c in parent.contents if c is not node
        )

        # Move all children from the original node to the new aside tag.
        # Per review, use `node.contents` to ensure all node types are preserved.
        # A static tuple is created to ensure safe iteration while moving children.
        for child in tuple(node.contents):
            aside_tag.append(child)

        # If the node's parent is a <p> tag and the node is the only significant
        # content within it, replace the entire <p> tag with the new <aside>.
        # This prevents creating empty <p> tags and maintains block-level semantics.
        if should_replace_parent_p:
            parent.replace_with(aside_tag)
        else:
            # Otherwise, just replace the node itself.
            node.replace_with(aside_tag)

        self.asides_created += 1
        log.debug("Transformed node to <aside>: %s", aside_tag.get("id", "no-id"))

    def get_metadata(self, status: PipelineStatus) -> dict[str, Any]:
        """Compiles and returns the execution log dictionary.

        Args:
            status: The final status of the pipeline run ('success', 'idle', or 'error').

        Returns:
            A dictionary conforming to the canonical metadata contract, containing
            final telemetry counts and status.

        Mutations:
            None.

        Rules & Limits:
            - **Output Contract:** The returned dictionary must be nested under the key
              `floating_element_processing` and contain the following keys:
              - `asides_created`: int
              - `containment_guard_rejections`: int
              - `density_guard_rejections`: int
              - `elements_evaluated`: int
              - `status`: str (The value of the `status` argument)
              - `execution_timestamp`: str (ISO 8601 format)
        """
        return {
            "floating_element_processing": {
                "asides_created": self.asides_created,
                "containment_guard_rejections": self.containment_guard_rejections,
                "density_guard_rejections": self.density_guard_rejections,
                "elements_evaluated": self.elements_evaluated,
                "status": status.value,
                "execution_timestamp": get_utc_timestamp(),
            },
        }

register_processor_factory(
    "floating_element_processor",
    FloatingElementProcessor,
)
