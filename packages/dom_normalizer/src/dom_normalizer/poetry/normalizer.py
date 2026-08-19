"""The main poetry normalization engine.

This module contains the `PoetryNormalizer` class, which orchestrates the
identification and transformation of poetic verse. It uses a `StructuralMatcher`
to find poetry candidates and then mutates the DOM to a standardized,
Pandoc-compatible format.

"""

from __future__ import annotations

import copy
import logging
from collections.abc import Mapping, Sequence
from typing import Any

from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString, PageElement

from ..core import BookStyleContext, PipelineStatus
from ..core.component_registry import register_processor_factory
from ..core.dom_utils import (
    coerce_class_list,
    generate_processor_metadata,
)
from ..core.list_utils import trim_text_from_tag_start
from .indentation_helper import PoetryIndentationHelper
from .matcher import MatchResult, StructuralMatcher
from .strategies import BasePoetryStrategy

log = logging.getLogger(__name__)


@register_processor_factory("poetry")
@register_processor_factory("poetry_normalizer")
class PoetryNormalizer:
    """Identifies and normalizes blocks of poetic verse into a standard structure."""

    def __init__(self, context: BookStyleContext):
        """Initializes the poetry normalizer and its structural matcher.

        Args:
            context: The shared context for the book.

        Returns:
            None

        Raises:
            None

        Mutations:
            - Initializes `self.matcher` with a new `StructuralMatcher` instance.
            - Initializes all telemetry counters to 0.
            - Loads `em_to_indent_ratio`, `px_to_em_ratio`, `percent_to_indent_ratio`,
              and `nbsp_to_indent_ratio` from `context.config`.

        Rules & Limits:
            - Instance Lifecycle: Assumes this instance is scoped to a single book.
        """
        self.context = context
        self.matcher = StructuralMatcher(context)
        self.indentation_helper = PoetryIndentationHelper(context)
        self.detected_poems_count = 0
        self.dialogue_blocks_excluded = 0
        self.geometric_rejections = 0

    def _is_high_priority_mode(self) -> bool:
        """Checks if the high poetry priority mode is enabled in the config.

        Args:
            None

        Returns:
            bool: True if high priority mode is enabled, False otherwise.
        """
        return getattr(self.context.config, "high_poetry_priority", False)

    def _collect_candidates(self, soup: BeautifulSoup) -> list[Tag]:
        """Collects candidate nodes for poetry analysis.

        It always includes <blockquote> elements. If the book is marked for
        high priority poetry processing, it also includes <div> elements that
        match registered container classes.

        Args:
            soup (BeautifulSoup): The DOM to search for candidates.

        Returns:
            list[Tag]: A list of candidate tags to be analyzed.
        """
        candidates = list(soup.find_all(self.context.config.poetry_candidate_tags))

        if not self._is_high_priority_mode():
            return candidates

        # In high-priority mode, perform a global scan for other potential
        # verse structures.
        #
        # NOTE:
        # We intentionally avoid scanning all <p> elements here because this is
        # very expensive on large documents and tends to generate many
        # low-quality candidates. Paragraph-level heuristics should be handled
        # by more targeted logic (e.g., class-based or context-based selection)
        # in the matcher or in a dedicated paragraph filter.
        potential_tags = self.context.config.poetry_high_priority_candidate_tags
        all_candidates = list(candidates)
        for tag_name in potential_tags:
            all_candidates.extend(soup.find_all(tag_name))

        # Filter out nodes that are descendants of other candidates to process
        # containers before their contents.
        candidate_set = set(all_candidates)
        root_candidates = []
        for cand in all_candidates:
            is_descendant = False
            parent = cand.parent
            while parent:
                if parent in candidate_set:
                    is_descendant = True
                    break
                parent = parent.parent
            if not is_descendant:
                root_candidates.append(cand)

        # Return unique candidates, preserving order
        return list(dict.fromkeys(root_candidates))

    def _process_candidate(self, candidate: Tag, soup: BeautifulSoup) -> Tag | None:
        """Processes a single candidate node for poetry normalization.

        This method calls the matcher to evaluate a candidate. If it's a match,
        it transforms the node into a poetry block. If the match was made by a
        heuristic strategy, it also invokes the `PoetryStrategyCompiler` to
        generate a new, declarative strategy configuration. If it's a rejection,
        it updates the appropriate telemetry counter. If it's a rejection,
        Args:
            candidate (Tag): The candidate node to process.
            soup (BeautifulSoup): The root BeautifulSoup object.

        Returns:
            Tag | None: The node that was actually processed if a match was found,
                otherwise None.
        """
        match_result = self.matcher.match(candidate)

        if match_result.match_type != "none":
            return self._handle_successful_match(candidate, soup, match_result)
        self._update_rejection_telemetry(match_result.rejection_reason)
        return None

    def _handle_successful_match(
        self,
        candidate: Tag,
        soup: BeautifulSoup,
        match_result: MatchResult,
    ) -> Tag:
        """Handles the transformation and telemetry for a successful poetry match.

        This method orchestrates the actions taken when a candidate is successfully
        identified as poetry. It logs the match, triggers strategy compilation for
        heuristic matches, transforms the DOM, and updates telemetry.

        Args:
            candidate: The tag that was matched.
            soup: The root BeautifulSoup object.
            match_result: The result object from the `StructuralMatcher`.

        Returns:
            Tag: The node that was actually transformed.

        Mutations:
            - Triggers DOM transformation via `_transform_to_poetry_block`.
            - Increments `self.detected_poems_count`.
        """
        strategy_id = match_result.strategy_id
        strategy = self.matcher.get_strategy_by_id(strategy_id) if strategy_id else None

        # Use the specific node identified by the matcher for transformation.
        # Fall back to the original candidate if not specified.
        node_to_transform = match_result.node_to_process or candidate

        self._transform_to_poetry_block(node_to_transform, soup, strategy)
        self.detected_poems_count += 1
        return node_to_transform

    def _update_rejection_telemetry(self, rejection_reason: str | None) -> None:
        """Updates telemetry counters based on the reason for a match rejection.

        Args:
            rejection_reason: The reason provided by the `StructuralMatcher`,
                which can be 'dialogue_excluded' or 'geometric_mismatch'.

        Returns:
            None

        Mutations:
            - Increments `self.dialogue_blocks_excluded` or `self.geometric_rejections`.
        """
        if rejection_reason == "dialogue_excluded":
            self.dialogue_blocks_excluded += 1
        elif rejection_reason == "geometric_mismatch":
            self.geometric_rejections += 1

    def process(self, soup: BeautifulSoup) -> tuple[BeautifulSoup, Mapping[str, Any]]:
        """Executes the isolation and token transformation of poetry structures.

        This method orchestrates the poetry normalization pipeline. It finds
        candidate blocks, evaluates them using the `StructuralMatcher`, and
        either mutates them into a canonical poetry format or logs the reason
        for rejection.

        Args:
            soup (BeautifulSoup): The in-memory DOM of the document to be processed.

        Returns:
            tuple[BeautifulSoup, dict[str, Any]]: A tuple containing the mutated soup
                object and a metadata dictionary summarizing the process.

        Raises:
            Exception: Per Global Directive #1, any unexpected native exceptions
                during processing will be caught, logged as CRITICAL, and re-raised.

        Mutations:
            - If a poetry block is detected, the original node(s) are replaced by a
              new `<div class="poetry-block">` structure.
            - The new block contains text and `<br>` tags for line breaks, compatible
              with Pandoc's line-block extension.
            - Increments internal telemetry counters based on match results.

        Rules & Limits:
            - Pipeline Order: Must execute strictly after `blockquote_processor`.
            - Candidate Selection:
                - All `<blockquote>` elements are universally inspected.
                - If the book is flagged as "High Poetry Priority" in its metadata,
                  a global heuristic scan for other block clusters is also performed.
            - DOM Mutation Schema (on match):
                - Root Wrapper: A `<div class="poetry-block">` is created. If the
                  original block was inside a `<blockquote>`, this `div` is
                  appended inside the preserved `<blockquote>`. Otherwise, the original
                  wrapper is replaced.
                - Line Structure: Each verse line is represented as text content
                  separated by `<br>` tags within the `line-block` div.
                - Indentation: Visual indents (`margin-left`, `text-indent`, `&nbsp;`)
                  are calculated and converted into leading em-space characters
                  (`\u2003`).
                - Stanza Breaks: Empty lines or consecutive `<br>` tags are
                  represented by an extra `<br>` tag, creating a blank line.
            - Telemetry:
                - On match: `detected_poems_count` is incremented.
                - On rejection: `dialogue_blocks_excluded` or `geometric_rejections`
                  is incremented based on the `rejection_reason` from the matcher.
            - Metadata Contract: The returned dictionary must conform to the YAML
              schema, including `status`, `mode_applied`, all counters,
              `newly_compiled_strategies`, and an
              `execution_timestamp`.
            - Full depth traversal: Yes.
        """
        processed_nodes: set[Tag] = set()
        candidates = self._collect_candidates(soup)

        for candidate in tuple(candidates):
            if candidate in processed_nodes or self.context.is_inside_code_block(
                candidate,
            ):
                continue

            processed_node = self._process_candidate(candidate, soup)
            if not processed_node:
                continue

            # Mark both the original candidate and the processed node as handled.
            # This prevents revisiting containers whose contents have already
            # been rewritten.
            processed_nodes.add(candidate)
            processed_nodes.add(processed_node)

        has_changes = self.detected_poems_count > 0
        status = PipelineStatus.SUCCESS if has_changes else PipelineStatus.SUCCESS_NOOP

        metadata = generate_processor_metadata(
            processor_key="poetry_normalization",
            status=status,
            mode_applied="high_priority"
            if self._is_high_priority_mode()
            else "standard",
            detected_poems_count=self.detected_poems_count,
            dialogue_blocks_excluded=self.dialogue_blocks_excluded,
            geometric_rejections=self.geometric_rejections,
        )
        return soup, metadata

    def _get_lines_from_target(
        self,
        target: Tag,
        strategy: BasePoetryStrategy | None,
    ) -> Sequence[Tag | list[PageElement]]:
        """Extracts poetry lines from a matched target.

        Args:
            target (Tag): The matched poetry container.
            strategy (BasePoetryStrategy | None): The strategy that matched the target.

        """
        return strategy.get_lines(target) if strategy else []

    def _calculate_indent(self, line_node: Tag) -> int:
        """Calculates a numeric indent level from styles and non-breaking spaces.

        Args:
            line_node (Tag): The node representing the line.

        Returns:
            int: The total calculated indentation level.
        """
        return self.indentation_helper.calculate_indent(line_node)

    def _process_line_content(
        self,
        line_content: Tag | list[PageElement],
    ) -> tuple[int, list[PageElement]]:
        """Processes a single line of poetry to extract indent and content nodes.

        This helper encapsulates the logic for calculating indentation and preparing
        the content of a single verse line for insertion into the final poetry block.

        Args:
            line_content (Tag | list[PageElement]): The raw line content, which can be
                a single tag or a list of mixed page elements.

        Returns:
            A tuple containing the calculated indent level (int) and a list of
            page elements representing the line's cleaned content.
        """
        indent = 0
        nodes_to_append = []

        if isinstance(
            line_content, Tag
        ):  # pyright: ignore[reportUnnecessaryIsInstance]
            indent = self._calculate_indent(line_content)
            # If a line is just for indentation (only &nbsp;), we don't want to
            # append the &nbsp; characters themselves as content.
            if not self.indentation_helper.is_indentation_only_line(
                line_content,
            ):
                nodes_to_append.extend(
                    copy.deepcopy(child) for child in line_content.children
                )
        elif isinstance(
            line_content, list
        ):  # pyright: ignore[reportUnnecessaryIsInstance]
            nodes_to_append.extend(copy.deepcopy(node) for node in line_content)

        self._strip_indentation_whitespace(nodes_to_append)
        return indent, nodes_to_append

    def _strip_indentation_whitespace(self, nodes_to_append: list[PageElement]) -> None:
        """Strips leading whitespace used for indentation from the first node in a line.

        This method precisely removes standard whitespace and non-breaking spaces
        that are part of the calculated indentation, preserving other meaningful
        leading whitespace. It modifies the list of nodes in-place and can handle
        the first node being either a text node or a tag containing text.

        Args:
            nodes_to_append: A list of page elements representing a line's content.
        """
        if not nodes_to_append:
            return

        first_node = nodes_to_append[0]

        # Get the text from the first node. For tags, we need all descendant strings.
        if isinstance(first_node, NavigableString):
            text = str(first_node)
        elif isinstance(
            first_node, Tag
        ):  # pyright: ignore[reportUnnecessaryIsInstance]
            # Concatenate all descendant strings to get the full text content
            # while preserving all whitespace characters like &nbsp;.
            text = "".join(first_node.strings)
        else:
            return

        first_non_ws_idx = 0
        while first_non_ws_idx < len(text) and text[first_non_ws_idx] in " \t\r\n":
            first_non_ws_idx += 1

        end_of_indent_idx = first_non_ws_idx
        while end_of_indent_idx < len(text) and text[end_of_indent_idx] == "\u00a0":
            end_of_indent_idx += 1

        chars_to_strip = end_of_indent_idx
        if chars_to_strip == 0:
            return

        if isinstance(first_node, NavigableString):
            nodes_to_append[0] = NavigableString(text[chars_to_strip:])
        else:  # first_node is guaranteed to be a Tag here due to prior checks
            trim_text_from_tag_start(first_node, chars_to_strip)

    def _populate_poetry_block(
        self,
        lines: Sequence[Tag | list[PageElement]],
        poetry_block: Tag,
        soup: BeautifulSoup,
    ) -> None:
        """Populates a poetry-block div with verse lines and stanza breaks.

        Args:
            lines (Sequence[Tag | list[PageElement]]): The extracted lines of poetry.
            poetry_block (Tag): The BeautifulSoup Tag for the poetry-block container.
            soup (BeautifulSoup): The BeautifulSoup object for creating new tags.

        Returns:
            None

        Mutations:
            - Appends text nodes and <br> tags to the poetry_block.
        """
        for i, line_content in enumerate(lines):
            if i > 0:
                poetry_block.append(soup.new_tag("br"))

            if self._is_stanza_break(line_content):
                continue

            indent, nodes_to_append = self._process_line_content(line_content)

            # After processing, check if there is any actual renderable text left.
            # A list with only an empty NavigableString is not considered to have
            # renderable content.
            has_renderable_nodes = any(
                self.indentation_helper.node_has_renderable_text(n)
                if isinstance(n, Tag)
                else str(n).strip()
                for n in nodes_to_append
            )

            if indent > 0:
                # For indented lines, always add a span with em-spaces.
                poetry_block.append(
                    soup.new_tag("span", string=self.context.config.poetry_indent_char * indent)
                )

            if has_renderable_nodes:
                poetry_block.extend(nodes_to_append)
            elif indent > 0:
                # This was an indentation-only line. Mark it explicitly and
                # ensure it is not collapsed by HTML formatters.
                indent_only_span = soup.new_tag("span")
                classes = coerce_class_list(indent_only_span.get("class"))
                classes.append(self.context.config.poetry_indent_only_line_class)
                indent_only_span["class"] = " ".join(classes)
                # Use a non-breaking space so downstream tools can detect and
                # preserve this line without relying on invisible characters.
                indent_only_span.string = "\u00a0"
                poetry_block.append(indent_only_span)

    def _is_stanza_break(self, line_content: Any) -> bool:
        """Checks if a line content represents a stanza break.

        Args:
            line_content (Any): The line content to evaluate.

        """
        if isinstance(line_content, list):
            # An empty list of nodes, resulting from consecutive <br> tags,
            # is considered a stanza break.
            return not line_content
        if isinstance(line_content, Tag):
            # A tag-based line is a stanza break if it has no renderable text.
            return not self.indentation_helper.node_has_renderable_text(line_content)
        return False

    def _replace_target_with_poetry_block(
        self,
        target: Tag,
        poetry_block: Tag,
    ) -> None:
        """Replaces or modifies the original target node with the new poetry block.

        If the target is a <blockquote>, it preserves the blockquote and wraps
        its normalized content with the new poetry_block div. Otherwise, it
        replaces the target entirely. This ensures that the semantic meaning of
        a quoted poem is not lost during transformation.
        """
        if target.name == "blockquote":
            target.clear()
            target.append(poetry_block)
        else:
            target.replace_with(poetry_block)

    def _transform_to_poetry_block(
        self,
        target: Tag,
        soup: BeautifulSoup,
        strategy: BasePoetryStrategy | None,
    ) -> None:
        """Mutates a matched block into the canonical poetry structure.

        Args:
            target (Tag): The matched poetry container.
            soup (BeautifulSoup): The soup object.
            strategy (BasePoetryStrategy | None): The strategy used for matching.

        Returns:
            None

        Mutations:
            - Delegates to helper methods to create and replace the target with a new
              poetry block.
        """
        lines = self._get_lines_from_target(target, strategy)
        if not lines:
            return

        poetry_block = soup.new_tag(
            "div", attrs={"class": self.context.config.poetry_block_class}
        )
        # The poetry_block is directly appended to the target or replaces it.

        self._populate_poetry_block(lines, poetry_block, soup)
        self._replace_target_with_poetry_block(target, poetry_block)
