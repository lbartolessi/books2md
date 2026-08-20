"""A semantic micro-normalizer for flattening and unifying emphasis styles.

Analytical Blueprint:
---------------------
Objective: Eliminate stylistic dispersion and redundant nesting of emphasis. It
translates various presentational tags and inline styles into a strict, binary
semantic format using canonical `<i>` and `<b>` tags. This ensures consistent
representation of emphasis for downstream processing.

This module operates as a Stage 2 processor, running after the heading
normalizer and before the blockquote processor.

Components:
    - EmphasisNormalizer: Orchestrates the normalization process.

Analytical Steps:
    1. Initial pass to convert semantic emphasis tags (`<em>`, `<strong>`) to
       physical equivalents (`<i>`, `<b>`) and flatten redundant nesting.
    2. Recursive traversal to propagate emphasis states down the DOM tree,
       wrapping text nodes in the appropriate canonical tags.

Global Free Functions (Module Level):
    - None present in the skeleton.

Class Methods (EmphasisNormalizer):
    - __init__: Initializes the normalizer with book-specific context and resets
      state counters: `italic_nodes_normalized`, `bold_nodes_normalized`,
      `nesting_fixes_count`, and `semantic_resets_triggered`.
    - process: Orchestrates the entire normalization pipeline. It first checks a
      guard clause to avoid processing content within code blocks. It then
      executes the normalization sub-routines in a specific order:
      1. `_normalize_native_tags`
      2. `_traverse_with_emphasis_state`
      Finally, it compiles and returns a metadata dictionary summarizing the
      operations performed, adhering to the specified output contract.
    - _normalize_native_tags: Performs an initial pass to convert pre-existing
      semantic emphasis tags (`<em>`, `strong>`) into their physical
      equivalents (`<i>`, `<b>`). It also purges redundant nested emphasis tags
      (e.g., `<i><i>text</i></i>` becomes `<i>text</i>`).
    - _traverse_with_emphasis_state: The core recursive traversal engine. It
      propagates an emphasis state (`italic`, `bold`) down the DOM.
    - _wrap_node_with_emphasis: Helper to wrap `PageElement` nodes with
      appropriate `<i>`, `<b>`, or `<i><b>` tags based on the emphasis state.
    - _ensure_canonical_nesting: Helper to enforce the `<i><b>` nesting order
      for combined emphasis by swapping `<b><i>` structures.

Transformation Rules:
    - `<em>` tags are converted to `<i>`.
    - `<strong>` tags are converted to `<b>`.
    - Redundant nested emphasis tags (`<i><i>`, `<b><b>`) are flattened.
    - Text nodes are wrapped with `<i>`, `<b>`, or `<i><b>` based on inherited
      emphasis state.
    - Combined emphasis always uses `<i><b>...</b></i>` nesting.

Output Format:
    - Returns a tuple of `(BeautifulSoup, dict[str, Any])` where the dictionary
      contains telemetry about the normalization process.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from typing import Any, cast

from bs4 import BeautifulSoup
from bs4.element import NavigableString, PageElement, Tag

from .core import BookStyleContext, PipelineStatus
from .core.component_registry import register_processor_factory
from .core.config import EngineConfiguration
from .core.dom_utils import (
    find_all_snapshot,
    generate_processor_metadata,
    select_snapshot,
    snapshot_iterator,
)

log = logging.getLogger(__name__)
EmphasisState = tuple[bool, bool]


class _ContrastiveEmphasisHandler:
    """A helper component to manage semantic reset logic for contrastive emphasis."""

    def __init__(self, normalizer: EmphasisNormalizer):
        """Initializes the handler with a reference to the main normalizer."""
        self.normalizer = normalizer
        self.context = normalizer.context

    def process_node(self, soup: BeautifulSoup, node: Tag, effective_state: EmphasisState) -> bool:
        """Processes a node to determine if a semantic reset is needed.

        If the node is a contrastive element found within an italic+bold context,
        this method triggers a semantic reset and returns True to signal that
        the node has been fully processed and should not be traversed further
        by the main loop.

        Args:
            node: The current node being traversed.
            effective_state: The effective emphasis state for the current node.

        Returns:
            True if a semantic reset was performed, False otherwise.
        """
        if self.normalizer.contrastive_detection_disabled:
            return False

        # A semantic reset is only triggered for a contrastive element inside a
        # combined italic and bold state.
        is_contrastive = self.context.is_contrastive_element(node)  # type: ignore [attr-defined]
        is_in_italic_bold_state = effective_state == (True, True)

        if is_contrastive and is_in_italic_bold_state:
            self._perform_semantic_reset(soup, node)
            self.normalizer.semantic_resets_triggered += 1
            return True
        return False

    def _validate_and_get_ancestors(
        self,
        contrastive_node: Tag,
    ) -> tuple[Tag | None, Tag | None]:
        """Validates the <i><b> ancestor structure and returns the tags.

        Args:
            contrastive_node: The node to validate against.

        Returns:
            A tuple containing the (i_grandparent, b_parent) if the structure
            is valid, otherwise (None, None).
        """
        # Explicitly type hint and cast the result of find_parent to Tag | None
        i_grandparent: Tag | None = contrastive_node.find_parent("i")
        b_parent: Tag | None = contrastive_node.find_parent("b")

        if not i_grandparent or not b_parent:
            log.warning(
                "Contrastive node %s not inside both <i> and <b> tags for semantic reset.",
                contrastive_node,
            )
            return None, None
        # After this check, i_grandparent and b_parent are guaranteed to be Tag.
        # We assert this to help Pylance with type narrowing.
        assert isinstance(i_grandparent, Tag)
        assert isinstance(b_parent, Tag)

        # Verify that b_parent is a descendant of i_grandparent to confirm <i><b> nesting.
        parent = b_parent.parent
        while parent:
            if parent is i_grandparent:
                return i_grandparent, b_parent
            parent = parent.parent

        log.warning(
            "Contrastive node %s not in expected <i>...<b> structure for semantic reset.",
            contrastive_node,
        )
        return None, None

    def _partition_and_extract_content(
        self,
        b_parent: Tag,
        contrastive_node: Tag,
    ) -> tuple[list[PageElement], list[PageElement]]:
        """Partitions content of b_parent around contrastive_node and extracts it.

        This method finds all content before and after the contrastive node
        within its bold parent and detaches all three parts from the DOM.

        Args:
            b_parent: The <b> tag containing the contrastive node.
            contrastive_node: The node to partition around.

        Returns:
            A tuple containing two lists of PageElements: (before_nodes, after_nodes).
        """
        all_b_children = tuple(snapshot_iterator(b_parent.contents))
        before_nodes: list[PageElement] = []
        after_nodes: list[PageElement] = []
        found_contrastive = False

        for child in all_b_children:
            if child is contrastive_node:
                found_contrastive = True
                continue
            if not found_contrastive:
                before_nodes.append(child)
            else:
                after_nodes.append(child)

        # Extract all parts from the DOM.
        for node in before_nodes:
            node.extract()
        contrastive_node.extract()
        for node in after_nodes:
            node.extract()

        return before_nodes, after_nodes

    def _normalize_partition_boundaries(
        self,
        content: list[PageElement],
        *,
        trim_left: bool,
        trim_right: bool,
    ) -> list[PageElement]:
        """Strips whitespace that was only used to separate the contrastive span.

        The semantic reset partitions text inside an `<i><b>` run around the
        contrastive node. Any whitespace immediately adjacent to the contrastive
        segment belongs to the surrounding text run, not to the plain contrastive
        span itself; trimming it avoids leaking stray spaces at the reset boundary.
        """
        if not content:
            return []

        normalized: list[PageElement] = []
        for index, node in enumerate(content):
            if not isinstance(node, NavigableString):
                normalized.append(node)
                continue

            text = str(node)
            if trim_left and index == 0:
                text = text.lstrip()
            if trim_right and index == len(content) - 1:
                text = text.rstrip()
            if text:
                normalized.append(NavigableString(text))

        return normalized

    def _create_emphasis_block(
        self, # The docstring for this method is not modified as per instructions.
        soup: BeautifulSoup,
        content: list[PageElement],
    ) -> Tag:
        """Creates a new <i><b>...</b></i> block with the given content.

        Use the live ancestor tag as the tag factory so the generated nodes stay
        attached to the same tree and do not depend on a detached `soup` root.
        """
        new_i = soup.new_tag("i")
        new_b = soup.new_tag("b")
        new_b.extend(content)
        new_i.append(new_b)
        return new_i

    def _perform_semantic_reset(self, soup: BeautifulSoup, contrastive_node: Tag) -> None:
        """Performs a semantic reset for a contrastive node in an italic+bold state.

        This is a tree-partition operation that splits the nearest `<i><b>`
        ancestor pair around the contrastive segment, re-wrapping the 'before'
        and 'after' parts and leaving the segment plain. This method ensures
        that the contrastive node itself is not wrapped in emphasis, while
        the surrounding content retains its inherited emphasis.

        Args:
            contrastive_node: The node identified as contrastive.

        Mutations:
            - Modifies the DOM by splitting and re-wrapping content.
            - The original `<i>` and `<b>` ancestor tags are decomposed if they become empty.
        """
        i_grandparent, b_parent = self._validate_and_get_ancestors(contrastive_node)
        if not i_grandparent or not b_parent:
            return

        # Partition the content of b_parent around the contrastive_node.
        # This also extracts contrastive_node, before_nodes, and after_nodes from the DOM.
        before_content, after_content = self._partition_and_extract_content(b_parent, contrastive_node)
        before_content = self._normalize_partition_boundaries(
            before_content,
            trim_left=False,
            trim_right=True,
        )
        after_content = self._normalize_partition_boundaries(
            after_content,
            trim_left=True,
            trim_right=False,
        )

        # 1. Insert the 'before' emphasis block before the original i_grandparent.
        if before_content:
            new_before_i = self._create_emphasis_block(soup, before_content)
            i_grandparent.insert_before(new_before_i)

        # 2. Insert the contrastive node itself, plain, before the original i_grandparent.
        i_grandparent.insert_before(contrastive_node)

        # 3. The original i_grandparent (and its child b_parent) will now contain the 'after' content.
        b_parent.clear() # Clear the original b_parent
        if after_content:
            b_parent.extend(after_content)

        # 4. Decompose any empty emphasis tags that remain.
        # Check for any child tags too, not just text, to ensure it's truly empty.
        if not b_parent.get_text(strip=True) and not b_parent.find(True):
            b_parent.decompose()
        # Check for any child tags too, not just text, to ensure it's truly empty.
        if not i_grandparent.get_text(strip=True) and not i_grandparent.find(True):
            i_grandparent.decompose()


@cast(
    Callable[[type["EmphasisNormalizer"]], type["EmphasisNormalizer"]],
    register_processor_factory(
        "emphasis_normalizer",
        factory_func=lambda context: EmphasisNormalizer(context),
    ),
)
class EmphasisNormalizer:
    """A semantic micro-normalizer for flattening and unifying emphasis styles."""

    def __init__(self, context: BookStyleContext) -> None:
        """Initializes the EmphasisNormalizer with book context and state.

        Args:
            context (BookStyleContext): The shared context for the book, providing
                access to configuration and helper methods like style detection.

        Returns:
            None

        Raises:
            None

        Mutations:
            - Sets `self.context` to the provided context object.
            - Initializes all telemetry counters to 0: `italic_nodes_normalized`,
              `bold_nodes_normalized`, `semantic_resets_triggered`, `nesting_fixes_count`.
            - Initializes `self.config` and `self.contrastive_detection_disabled`.

        Rules & Limits:
            - Instance Lifecycle: Assumes this instance is scoped to a single book and
              is never shared between different books, per Global Directive #3.
        """
        self.context = context
        self.italic_nodes_normalized: int = 0
        self.bold_nodes_normalized: int = 0
        self.semantic_resets_triggered: int = 0
        self.nesting_fixes_count: int = 0
        # Defer to a configuration flag. This is disabled by default as the
        # feature is not fully implemented. Explicitly type hint config.
        self.config: EngineConfiguration = context.config
        self.contrastive_detection_disabled = not getattr(
            self.config,
            "enable_contrastive_emphasis",
            False,
        )
        self.contrastive_handler = _ContrastiveEmphasisHandler(self)

    def process(self, soup: BeautifulSoup) -> tuple[BeautifulSoup, Mapping[str, Any]]:
        """Orchestrates the emphasis normalization process for a document.

        This is the main entry point for the normalizer. It flattens and unifies
        all forms of emphasis into canonical `<i>` and `<b>` tags by executing
        a series of normalization and traversal steps.

        Args:
            soup (BeautifulSoup): The in-memory DOM of the document to be processed.

        Returns:
            A tuple containing the mutated soup object and a metadata dictionary.

        Mutations:
            - The input `soup` object is modified in-place by the internal helper
              methods (`_normalize_native_tags`, `_traverse_with_emphasis_state`,
              and `_flatten_redundant_tags`).

        Rules & Limits:
            - Execution Order: Internal methods are called in a strict sequence:
              1. `_normalize_native_tags(soup)`
              2. `_traverse_with_emphasis_state(soup, (False, False))`
              3. `_flatten_redundant_tags(soup, "i")`
              4. `_flatten_redundant_tags(soup, "b")`
            - Immunity Protocol: If `self.context.is_inside_code_block(soup)` returns
              True, processing is aborted.
            - Status Logic: The final status is 'success' if any nodes were normalized
              or nesting was fixed. Otherwise, the status is 'idle'.
            - Metadata Contract: The returned dictionary conforms to the standard structure.

        """
        if self.context.is_inside_code_block(soup):
            log.debug(
                "Skipping emphasis normalization for document as it's a code block.",
            )
            return soup, generate_processor_metadata(
                processor_key="emphasis_normalization",
                status=PipelineStatus.SKIPPED,
                italic_nodes_normalized=0,
                bold_nodes_normalized=0,
                semantic_resets_triggered=0,
                nesting_fixes_count=0,
                contrastive_detection_disabled=True,
            )

        self._normalize_native_tags(soup)
        if soup.body:
            self._traverse_with_emphasis_state(soup, soup.body, (False, False))
        # Final cleanup pass to flatten any redundant tags created by the traversal.
        # This robustly handles any double-wrapping that may have occurred.
        # Per review, this is a safe and correct way to handle redundant nesting.
        self._flatten_redundant_tags(soup, "i")
        self._flatten_redundant_tags(soup, "b")

        has_changes = (
            self.italic_nodes_normalized > 0
            or self.bold_nodes_normalized > 0
            or self.nesting_fixes_count > 0
        )
        status = PipelineStatus.SUCCESS if has_changes else PipelineStatus.SUCCESS_NOOP

        metadata = generate_processor_metadata(
            processor_key="emphasis_normalization",
            status=status,
            italic_nodes_normalized=self.italic_nodes_normalized,
            bold_nodes_normalized=self.bold_nodes_normalized,
            semantic_resets_triggered=self.semantic_resets_triggered,
            nesting_fixes_count=self.nesting_fixes_count,
            contrastive_detection_disabled=self.contrastive_detection_disabled,
        )

        return soup, metadata

    def _normalize_native_tags(self, soup: BeautifulSoup) -> None:
        """Converts semantic tags to physical tags and purges redundant nesting.

        This method performs a preliminary pass over the DOM to unify common
        semantic emphasis tags (`<em>`, `<strong>`) into their physical
        equivalents (`<i>`, `<b>`) and to flatten identically nested tags.

        Args:
            soup (BeautifulSoup): The in-memory DOM of the document.

        Mutations:
            - Renames all `<em>` tags to `<i>` in-place.
            - Renames all `<strong>` tags to `<b>` in-place.
            - Flattens redundant nested tags (e.g., `<i><i>text</i></i>`) by
              unwrapping the inner tag, effectively merging them.

        Rules & Limits:
            - Target Tags: `<em>`, `<strong>`. The specification also mentions `<ins>`
              but does not define its mapping; this method only handles `em` and `strong`.
            - Tag Case: The target tags are converted to lowercase `<i>` and `<b>`.
            - Full depth traversal: Yes, to find all instances of target tags.
        """
        self._convert_semantic_tag(soup, "em", "i")
        self._convert_semantic_tag(soup, "strong", "b")
        self._flatten_redundant_tags(soup, "i")
        self._flatten_redundant_tags(soup, "b")

    # region: Tag Conversion and Flattening
    def _convert_semantic_tag(
        self,
        soup: BeautifulSoup,
        from_tag: str,
        to_tag: str,
    ) -> None:
        """Converts all instances of one tag to another, e.g., <em> to <i>.

        This function finds all tags with the `from_tag` name, renames them to
        `to_tag`, and updates the relevant normalization counters.
        Returns:
            None

        Raises:
            None

        Mutations:
            - Renames all instances of `from_tag` to `to_tag` in-place.
            - Increments `self.italic_nodes_normalized` or `self.bold_nodes_normalized`
              for each tag converted.
            - Skips tags inside code blocks.

        Args:
            soup (BeautifulSoup): The BeautifulSoup object to modify.
            from_tag (str): The name of the tag to convert from.
            to_tag (str): The name of the tag to convert to.
        """
        for tag in find_all_snapshot(soup, from_tag):
            if not isinstance(tag, Tag):
                continue
            if self.context.is_inside_code_block(tag):
                continue
            tag.name = to_tag
            if to_tag == "i":
                self.italic_nodes_normalized += 1
            elif to_tag == "b":
                self.bold_nodes_normalized += 1
            log.debug("Converted <%s> to <%s>: %s", from_tag, to_tag, tag)
            # After conversion, the tag might need to be flattened if it creates
            # a redundant nesting (e.g., <em><i>text</i></i> -> <i><i>text</i></i>)
            # This is handled by the subsequent _flatten_redundant_tags calls in process().

    def _flatten_redundant_tags(self, soup: BeautifulSoup, tag_name: str) -> None:
        """Finds and unwraps redundant nested tags (e.g., <i><i>text</i></i>).

        This method iteratively finds any `<tag_name>` that is a descendant of
        another `<tag_name>` and unwraps the inner tag. The process repeats
        until no more such nested tags can be found, ensuring that structures
        like `<i><i><i>text</i></i></i>` are fully flattened.

        Returns:
            None

        Raises: # pyright: ignore[reportUnusedMethod]
            None

        Rules & Limits:
             - Full depth traversal: Yes, to find all instances of target tags.

        Args:
            soup (BeautifulSoup): The BeautifulSoup object to modify.
            tag_name (str): The name of the tag to flatten (e.g., 'i' or 'b').
        """
        for passes_count in range(self.config.max_flatten_passes):
            # Find all instances of a tag nested inside another tag of the same name.
            # Use the direct child selector '>' to avoid complex descendant issues
            # that can lead to infinite loops with unwrap().
            selector = f"{tag_name} > {tag_name}"
            all_redundant_tags_in_pass = select_snapshot(soup, selector)

            tags_to_unwrap = [
                tag
                for tag in all_redundant_tags_in_pass
                if isinstance(tag, Tag) and not self.context.is_inside_code_block(tag)
            ]

            if not tags_to_unwrap:
                log.debug(
                    "Completed flattening for <%s> tags in %d pass(es).",
                    tag_name,
                    passes_count,
                )
                return  # Convergence achieved

            for inner_tag in tags_to_unwrap:
                inner_tag.unwrap()
                log.debug("Flattened nested <%s> tag outside code block.", tag_name)

        # If the loop completes without returning, it means we hit the pass limit.
        log.warning(
            "Emphasis Normalizer: Flattening for <%s> tags reached max passes (%d). " # pyright: ignore[reportUnknownArgumentType]
            "There may be remaining nested tags.",
            tag_name,
            self.config.max_flatten_passes,
        )

    # endregion

    def _get_wrapping_actions(
        self,
        node_to_wrap: PageElement,
        desired_state: EmphasisState,
    ) -> EmphasisState:
        """Determines the necessary wrapping actions based on desired state and current DOM.

        This helper checks if a node already has the desired emphasis from its own
        tag name or from an ancestor to avoid redundant wrapping.

        Args:
            node_to_wrap (PageElement): The node to be potentially wrapped.
            desired_state (EmphasisState): The target emphasis state (is_italic, is_bold).

        Returns:
            EmphasisState: A tuple (is_italic, is_bold) indicating what wrapping is
                actually needed.
        """
        is_italic_needed, is_bold_needed = desired_state

        if isinstance(node_to_wrap, Tag):
            if node_to_wrap.name == "i":
                is_italic_needed = False
            if node_to_wrap.name == "b":
                is_bold_needed = False

        if is_italic_needed and node_to_wrap.find_parent("i"):
            is_italic_needed = False
        if is_bold_needed and node_to_wrap.find_parent("b"):
            is_bold_needed = False

        return is_italic_needed, is_bold_needed

    def _wrap_node_with_emphasis(
        self,
        soup: BeautifulSoup,
        node_to_wrap: PageElement,
        state: EmphasisState,  # This is the desired state for the node
    ) -> PageElement:
        """Wraps a PageElement (Tag or NavigableString) in `<i>`, `<b>`, or `<i><b>` based on the desired state.

        This method uses `bs4.element.Tag.wrap()` to safely modify the DOM in-place,
        avoiding recursive structures that can cause infinite loops during traversal.
        It handles single emphasis (`<i>` or `<b>`) and combined emphasis (`<i><b>`),
        ensuring canonical nesting. It also checks ancestors to avoid redundant
        wrapping for single emphasis.

        Args:
            node_to_wrap (PageElement): The node to wrap.
            state (EmphasisState): The emphasis state (is_italic, is_bold).

        Returns:
            PageElement: The new outer wrapper tag if wrapping occurred, otherwise
                the original node.

        Mutations:
            - Wraps the `node_to_wrap` with a new `<i>`, `<b>`, or `<i><b>` tag.
            - Increments `self.italic_nodes_normalized` and/or `self.bold_nodes_normalized`
              when a wrapper is created.
        """
        if not node_to_wrap.get_text(strip=True) or not node_to_wrap.parent:
            return node_to_wrap

        is_italic_needed, is_bold_needed = self._get_wrapping_actions(
            node_to_wrap,
            state,
        )

        if is_italic_needed and is_bold_needed:
            return self._wrap_combined_emphasis(soup, node_to_wrap)
        if is_italic_needed:
            return self._wrap_single_emphasis(soup, node_to_wrap, "i")
        if is_bold_needed:
            return self._wrap_single_emphasis(soup, node_to_wrap, "b")
        return node_to_wrap

    def _wrap_combined_emphasis(
        self,
        soup: BeautifulSoup,
        node_to_wrap: PageElement,
    ) -> Tag:
        """Wraps a node with canonical `<i><b>` tags for combined emphasis.

        Args:
            node_to_wrap (PageElement): The node to wrap.
            soup (BeautifulSoup): The BeautifulSoup instance for creating new tags.

        Returns:
            Tag: The new outer `<i>` wrapper tag.
        """
        outer_wrapper = soup.new_tag("i")
        inner_wrapper = soup.new_tag("b")
        node_to_wrap.wrap(inner_wrapper)
        inner_wrapper.wrap(outer_wrapper)
        self.italic_nodes_normalized += 1
        self.bold_nodes_normalized += 1
        log.debug("Wrapped node with <i><b> emphasis.")
        return outer_wrapper # outer_wrapper is already cast to Tag

    def _wrap_single_emphasis(
        self,
        soup: BeautifulSoup,
        node_to_wrap: PageElement,
        tag_name: str,
    ) -> Tag:
        """Wraps a node with a single emphasis tag (`<i>` or `<b>`).

        Args:
            node_to_wrap (PageElement): The node to wrap.
            tag_name (str): The name of the tag to use for wrapping ('i' or 'b').
            soup (BeautifulSoup): The BeautifulSoup instance for creating new tags.

        Returns:
            Tag: The new wrapper tag.
        """
        wrapper = soup.new_tag(tag_name)
        node_to_wrap.wrap(wrapper)
        if tag_name == "i":
            self.italic_nodes_normalized += 1
            log.debug("Wrapped node with <i> emphasis.")
        else:  # tag_name == "b"
            self.bold_nodes_normalized += 1
            log.debug("Wrapped node with <b> emphasis.")
        return wrapper # wrapper is already cast to Tag

    def _process_string_node(
        self,
        soup: BeautifulSoup,
        node: NavigableString,
        inherited_state: EmphasisState,
    ) -> None:
        """Processes a NavigableString, wrapping it if it contains text."""
        if node.strip():
            self._wrap_node_with_emphasis(soup, node, inherited_state)

    def _process_tag_node(
        self,
        soup: BeautifulSoup,
        node: Tag,
        inherited_state: EmphasisState,
    ) -> None:
        """Processes a Tag, calculating the new state and recursing on children."""
        if self.context.is_inside_code_block(node):
            return

        # This is the state that children of this node will inherit.
        effective_state = self._get_cumulative_state(node, inherited_state)

        # Handle semantic reset BEFORE any wrapping or further traversal.
        if self.contrastive_handler.process_node(soup, node, effective_state):
            return

        # If the node is not an emphasis tag itself, check if it introduces
        # a new emphasis state via classes. If so, wrap it.
        if node.name not in {"i", "b"} and effective_state != inherited_state:
            self._wrap_node_with_emphasis(soup, node, effective_state)

        # Traverse children with the new effective state.
        for child in snapshot_iterator(node.children):
            self._traverse_with_emphasis_state(soup, child, effective_state)

        # After children are processed, ensure canonical nesting for this node
        # if it's an emphasis tag.
        if node.name in {"i", "b"}:
            self._ensure_canonical_nesting(node)

    def _traverse_with_emphasis_state(
        self,
        soup: BeautifulSoup,
        current_node: PageElement,
        inherited_state: EmphasisState,
    ) -> None:
        """Dispatches traversal to the appropriate handler based on node type."""
        if isinstance(current_node, NavigableString):
            self._process_string_node(soup, current_node, inherited_state)
        elif isinstance(current_node, Tag):
            self._process_tag_node(soup, current_node, inherited_state)

    def _get_node_own_emphasis_state(self, node: PageElement) -> EmphasisState:
        """Determines if a node itself is italic or bold based on its name or class."""
        if not isinstance(node, Tag):
            return False, False
        node_is_i = node.name == "i" or self.context.is_italic_element(node)
        node_is_b = node.name == "b" or self.context.is_bold_element(node)
        return node_is_i, node_is_b

    def _get_cumulative_state(
        self,
        node: Tag,
        inherited_state: EmphasisState,
    ) -> EmphasisState:
        """Calculates the cumulative emphasis state for a node's descendants.

        This combines the inherited state from the parent with the node's own
        emphasis state (from its tag or class).

        Args:
            node: The current tag to evaluate.
            inherited_state: The emphasis state from the parent.

        Returns:
            The new cumulative emphasis state.
        """
        node_is_italic, node_is_bold = self._get_node_own_emphasis_state(node)
        return (
            inherited_state[0] or node_is_italic,
            inherited_state[1] or node_is_bold,
        )

    # region: Canonical Nesting Enforcement
    def _is_pure_i_container(self, node: Tag) -> bool:
        """Checks if a <b> tag is a pure container of only <i> tags.

        A pure container is a `<b>` tag that contains only `<i>` tags and/or
        insignificant whitespace. It must contain at least one `<i>` tag.

        Raises:
            None

        Mutations:
            None.

        Args:
            node (Tag): The `<b>` tag to evaluate.

        Returns:
            bool: True if the node is a pure container, False otherwise.
        """
        if node.name != "b":
            return False

        has_i_child = False
        for child in node.children:
            if isinstance(child, NavigableString) and child.strip():
                # Contains significant text, not a pure container.
                return False
            if isinstance(child, Tag):
                if child.name == "i":
                    has_i_child = True
                else:
                    # Contains other tags, not a pure container.
                    return False
        return has_i_child

    def _ensure_canonical_nesting(self, node: Tag) -> None:
        """Ensures `<i><b>` nesting order for combined emphasis.

        If a `<b>` tag contains only `<i>` tags (and insignificant whitespace),
        this indicates a non-canonical nesting that should be swapped to the
        canonical `<i><b>...</b></i>` order.


        Raises:
            None

        Mutations:
            - If a non-canonical `<b><i>...</i></b>` structure is found, it renames
              the outer `<b>` to `<i>` and all inner `<i>` tags to `<b>`.
            - Increments `self.nesting_fixes_count`.

        Args:
            node (Tag): The `Tag` to inspect and potentially re-nest.

        Returns:
            None
        """
        # Per code review: This transformation is safe because of the strict
        # `_is_pure_i_container` guard, which ensures the `<b>` tag only
        # contains `<i>` tags and insignificant whitespace. Swapping tag names
        # via `tag.name = 'new_name'` preserves all attributes on the tag.
        # Therefore, attributes on the outer `<b>` tag correctly move to the
        # new outer `<i>` tag, and attributes on inner `<i>` tags correctly
        # move to the new inner `<b>` tags, preserving all metadata.
        if self._is_pure_i_container(node):
            log.debug("Re-nesting pure non-canonical <b><i>...</i></b> container.")
            node.name = "i"
            for child in snapshot_iterator(node.children):
                if isinstance(child, Tag) and child.name == "i":
                    child.name = "b"
            self.nesting_fixes_count += 1

    # endregion
