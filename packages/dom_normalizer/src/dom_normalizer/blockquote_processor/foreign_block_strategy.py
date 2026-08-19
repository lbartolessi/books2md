"""Identifies quotations by grouping paragraphs of the same foreign language."""

from __future__ import annotations

import logging
import re

from bs4 import BeautifulSoup, Tag

from ..core import BookStyleContext
from .base_strategy import PROCESSOR_UNBOUND_MSG, BaseBlockquoteStrategy

log = logging.getLogger(__name__)


class ForeignBlockStrategy(BaseBlockquoteStrategy):
    """Identifies quotations by grouping paragraphs of the same foreign language.

    This is the lowest-priority strategy (Priority 5). It serves as a fallback
    to group contiguous paragraphs that are all marked with a `lang` attribute
    different from the book's primary language. This is a useful heuristic for
    capturing long quotations in another language.
    """

    def find_and_apply(
        self,
        start_node: Tag,
        context: BookStyleContext,
        soup: BeautifulSoup,
    ) -> list[Tag] | None:
        """Finds and applies the foreign language block strategy (Priority 5).

        This method identifies quotations by grouping contiguous paragraphs that
        are marked with the same foreign language. If a valid sequence is found,
        it is wrapped in a `<blockquote>` and the list of processed nodes is
        returned.

        Mutations:
            - Wraps the identified foreign language nodes in a new `<blockquote>`
              element.

        Rules & Limits:
            - This is the lowest priority strategy (Priority 5).
            - Full depth traversal: Yes.
        """
        sequence = self._collect_sequence(start_node, context)

        if sequence and self._is_candidate_valid(sequence):
            # The language is guaranteed to be consistent by _collect_sequence.
            foreign_lang = self._get_foreign_lang(sequence[0], context)
            assert foreign_lang is not None, (
                "foreign_lang should not be None if _collect_sequence returned a sequence."
            )
            if blockquote := self._wrap_nodes_in_blockquote(
                sequence,
                soup,
                bq_class="foreign-block",
            ):
                blockquote["lang"] = foreign_lang
                for node in sequence:
                    if "lang" in node.attrs:
                        del node["lang"]
            assert self.processor, PROCESSOR_UNBOUND_MSG
            self.processor.foreign_blocks_identified_count += 1
            return sequence
        return None

    def _normalize_lang(self, lang_attr: str) -> str | None:
        """Normalizes a language attribute string to its base language code.

        This prevents regional variants (e.g., 'en-US', 'pt_BR') from being
        incorrectly flagged as foreign in a book with a base language of 'en' or
        'pt' by splitting on both hyphens and underscores.

        The function is defensive against malformed or empty BCP-47 tags:
        it filters out empty segments (e.g., for values like '-US' or 'en--US')
        and returns ``None`` when no valid language subtag can be determined.

        Args:
            lang_attr (str): The raw language attribute string from the DOM.

        Returns:
            str | None: The normalized base language code in lowercase, or
            ``None`` if the input does not contain any valid non-empty segment.
        Mutations:
            None.

        Rules & Limits:
            - Normalization Rule: The implementation must be equivalent to
              `lang_attr.strip().split('-')[0].lower()`.
        """
        stripped = lang_attr.strip()
        if not stripped:
            return None

        # Split on '-' and '_' and discard empty segments to avoid returning an
        # empty normalized language for malformed tags such as '-US', '--',
        # '_US', or '__'. This supports both BCP-47 style tags (e.g. "en-US")
        # and common underscore-based tags (e.g. "pt_BR").
        segments = [segment for segment in re.split(r"[-_]", stripped) if segment]
        return segments[0].lower() if segments else None

    def _get_foreign_lang(self, node: Tag, context: BookStyleContext) -> str | None:
        """Determines if a node is marked with a foreign language.

        Args:
            node (Tag): The node to inspect.
            context (BookStyleContext): The shared context for the book, which
                contains the `primary_language`.

        Returns:
            str | None: The foreign language code if found, otherwise None.

        Mutations:
            None.

        Rules & Limits:
            - A language is considered foreign if its normalized form is not equal
              to `context.primary_language`.
            - Node Type Safety: Expects a `Tag`. Returns `None` if `lang` attribute
              is not found.
        """
        if node.name != "p":
            return None

        # Normalize the book's primary language for a robust comparison.
        primary_lang = (
            self._normalize_lang(context.primary_language)
            if context.primary_language
            else None
        )
        if not primary_lang:
            # If the book's primary language is unknown, we cannot determine
            # what is "foreign".
            return None

        lang_attr = node.get("lang")
        if not lang_attr or not isinstance(lang_attr, str):
            return None

        normalized_lang = self._normalize_lang(lang_attr)
        if normalized_lang and normalized_lang != primary_lang:
            return normalized_lang
        return None

    def _collect_sequence(
        self,
        start_node: Tag,
        context: BookStyleContext,
    ) -> list[Tag] | None:
        """Collects contiguous sibling nodes that share the same foreign language.

        This method traverses sibling nodes, skipping over non-content elements
        (like whitespace or comments) to group only relevant paragraph-like tags. The
        sequence is broken by any content that does not share the same language.

        Args:
            start_node (Tag): The first node in the foreign language sequence.
            context (BookStyleContext): The shared context for the book.
            foreign_lang (str): The normalized foreign language code that all
                nodes in the sequence must share.

        Rules & Limits:
            - Grouping Rule: Appends consecutive sibling paragraphs if and only if
              their normalized `lang` subtag exactly matches `foreign_lang`.
            - Sibling Traversal: Safely traverses `previous_sibling` and
              `next_sibling` to find the full sequence.
        """
        assert self.config is not None, "Config not bound to strategy"
        if (
            start_node.name != "p"
            or start_node.find_parent("blockquote")
            or len(start_node.get_text(strip=True)) < self.config.foreign_block_min_length
        ):
            return None

        foreign_lang = self._get_foreign_lang(start_node, context)
        if not foreign_lang:
            return None

        # Pass 1: Find the true start of the sequence by traversing backwards.
        first_node_in_sequence = start_node
        node_iterator = start_node
        while True:
            prev_sibling = self._get_prev_non_ignorable_sibling(node_iterator) # pyright: ignore[reportOptionalOperand]
            if (
                not prev_sibling
                or prev_sibling.name not in {"p", "div"}
                or self._get_foreign_lang(prev_sibling, context) != foreign_lang
            ):
                break
            first_node_in_sequence = prev_sibling
            node_iterator = prev_sibling

        sequence = []
        node_iterator = first_node_in_sequence
        while (
            node_iterator
            and node_iterator.name in {"p", "div"}
            and self._get_foreign_lang(node_iterator, context) == foreign_lang
        ):
            sequence.append(node_iterator)
            node_iterator = self._get_next_non_ignorable_sibling(node_iterator) # pyright: ignore[reportOptionalOperand]

        return sequence
