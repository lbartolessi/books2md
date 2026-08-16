"""
A thread-isolated container for a single book's structural style profile.

This module provides the foundational components for the entire `dom_normalizer`
library. The `BookStyleContext` class is responsible for parsing a book's CSS
and building an in-memory profile of "molecular" class compounds that define
specific layouts (e.g., floating elements, blockquotes, bold/italic text).

It provides methods to query this profile, allowing other normalizers to
identify elements based on their styling rather than just their tags.
"""

import logging
import re
from typing import Final

from bs4 import Tag

from dom_normalizer.core.dom_utils import coerce_class_list, normalize_style_attribute

from .config import EngineConfiguration
from .constants import (
    BLOCKQUOTE_ELEMENT_CLASS,
    BOLD_ELEMENT_CLASS,
    CODE_CLASSES,
    FLOATING_ELEMENT_CLASS,
    ITALIC_ELEMENT_CLASS,
)
from .lang_codes import ISOLanguageCode

log = logging.getLogger(__name__)

_MIN_INDENT_EM_REM: Final[float] = 1.5
_MIN_INDENT_PX: Final[int] = 24


class BookStyleContext:
    """A thread-isolated container for a single book's structural style profile.

    This class is responsible for parsing a book's CSS and building an in-memory
    profile of "molecular" class compounds that define specific layouts (e.g.,
    floating elements, blockquotes, bold/italic text). It provides methods to
    query this profile, allowing other normalizers to identify elements based on
    their styling rather than just their tags.

    It requires a pre-validated `ISOLanguageCode` to enforce type safety and
    ensure that all language-dependent operations have a valid context.

    Attributes:
        primary_language: The validated primary language of the book.
        config: The active `EngineConfiguration` for the pipeline.
        floating_compounds: A set of frozensets, where each inner frozenset is a
            "compound" of CSS classes that defines a floating element.
        blockquote_compounds: A set of frozensets for classes that define
            indented/blockquote elements.
        italic_compounds: A set of frozensets for classes that define italic styling.
        bold_compounds: A set of frozensets for classes that define bold styling.

    Raises:
        TypeError: If `primary_language` is not an instance of `ISOLanguageCode`.

    Rules & Logic:
        - Default compounds like `frozenset(["floating-element"])` are added at
          initialization to support inline style normalization.
    """

    _INDENT_VALUE_RX = re.compile(
        # Numeric values are restricted to standard integer or decimal forms:
        # - "12" or "12.5" are allowed
        # - Malformed values like "1." or ".5" are rejected here and by _is_indent_declaration
        # If leading-decimal formats need to be supported in the future, they should be
        # added explicitly and documented.
        r"(?:margin|padding)-left\s*:\s*(\d+(?:\.\d+)?)\s*(em|rem|px)",
        re.IGNORECASE,
    )
    _FLOAT_DECL_RX: Final[re.Pattern[str]] = re.compile(r"\bfloat\s*:", re.IGNORECASE)
    _POSITION_DECL_RX: Final[re.Pattern[str]] = re.compile(
        r"\bposition\s*:\s*(absolute|fixed)\b",
        re.IGNORECASE,
    )
    _ITALIC_DECL_RX: Final[re.Pattern[str]] = re.compile(
        r"font-style\s*:\s*italic\b",
        re.IGNORECASE,
    )
    _BOLD_DECL_RX: Final[re.Pattern[str]] = re.compile(
        r"font-weight\s*:\s*(?:bold|[6-9]00)\b",
        re.IGNORECASE,
    )

    # Per review, add safeguards against deeply nested or malformed CSS.
    _MAX_BRACE_DEPTH: Final[int] = 50
    _MAX_SCAN_ITERATIONS: Final[int] = 1_000_000

    def __init__(
        self,
        primary_language: ISOLanguageCode,
        epub_css_content: str = "",
        config: EngineConfiguration | None = None,
    ) -> None:

        if not isinstance(
            primary_language,
            ISOLanguageCode,
        ):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError(
                "Orchestration Contract Violation: 'primary_language' must be an instance of ISOLanguageCode. "
                f"Received: {type(primary_language)}",
            )

        self.primary_language: Final[ISOLanguageCode] = primary_language
        self.config: EngineConfiguration = config or EngineConfiguration()

        # Molecular compound storage for structural signature matching
        self.floating_compounds: set[frozenset[str]] = {
            frozenset([FLOATING_ELEMENT_CLASS]),
        }
        self.blockquote_compounds: set[frozenset[str]] = {
            frozenset([BLOCKQUOTE_ELEMENT_CLASS]),
        }
        self.italic_compounds: set[frozenset[str]] = {
            frozenset([ITALIC_ELEMENT_CLASS]),
        }
        self.bold_compounds: set[frozenset[str]] = {frozenset([BOLD_ELEMENT_CLASS])}

        if epub_css_content:
            self._harvest_layout_classes(epub_css_content)

    @staticmethod
    def _find_matching_brace_end(text: str, start_index: int) -> int:
        """Finds the index of the matching closing brace for an opening brace.

        This helper function starts scanning from `start_index` (which should be
        the position of an opening brace) and counts nested braces to find the
        corresponding closing brace. It includes safeguards against excessively
        deep nesting or long scans in malformed CSS.

        Args:
            text: The string to search within.
            start_index: The index of the opening brace '{'.

        Returns:
            The index of the position *after* the matching closing brace '}', or
            -1 if not found or if a safeguard limit is exceeded.
        """
        brace_depth = 1
        i = start_index + 1
        iterations = 0
        while (
            i < len(text) and iterations < BookStyleContext._MAX_SCAN_ITERATIONS
        ):  # NOSONAR
            if text[i] == "{":
                brace_depth += 1
                if brace_depth > BookStyleContext._MAX_BRACE_DEPTH:
                    return -1  # Exceeded max depth, treat as malformed
            elif text[i] == "}":
                brace_depth -= 1
                if brace_depth == 0:
                    return i + 1
            i += 1
            iterations += 1
        return -1  # Unmatched brace or exceeded iterations

    @staticmethod
    def _recover_from_malformed_media_block(css_text: str, current_index: int) -> int:
        """Advances the parser past a malformed @media block.

        This is a defensive recovery mechanism. When an unclosed or malformed
        `@media` block is detected, this function finds the next likely rule
        boundary (a '}' or newline) and moves the parser's index past it.

        Args:
            css_text: The full CSS string being parsed.
            current_index: The index where the malformed block was detected.

        Returns:
            The new index for the parser to continue from.
        """
        next_brace = css_text.find("}", current_index)
        next_newline = css_text.find("\n", current_index)
        positions = [p for p in (next_brace, next_newline) if p != -1]
        # Skip to the character after the recovery point, or to the end.
        return min(positions) + 1 if positions else len(css_text)

    @staticmethod
    def _strip_css_comments(css_text: str) -> str:
        """Strips C-style /* ... */ comments from a CSS string.

        This parser is stateful to avoid incorrectly stripping comment-like
        sequences from within string literals or URLs (e.g., in `content` or
        `url()` properties). It uses a regex to find either comments or string
        literals, then selectively removes only the comments.
        """
        # This regex finds either a comment block or a string literal.
        token_finder = re.compile(
            r'/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'',
            re.DOTALL,
        )

        def replacer(match: re.Match[str]) -> str:
            """Replace comments with empty string, keep string literals."""
            return "" if match.group(0).startswith("/*") else match.group(0)

        return token_finder.sub(replacer, css_text)

    @staticmethod
    def _strip_css_media_blocks(css_text: str) -> str:
        """Strips @media blocks from a CSS string, correctly handling nesting.

        This method is designed to be resilient against malformed CSS. If it
        encounters an unclosed `@media` block, it defensively skips forward to
        the next likely rule boundary (a '}' or newline) to prevent the
        malformed block from corrupting the rest of the style analysis.
        """
        clean_css = BookStyleContext._strip_css_comments(css_text)
        output = []
        i = 0
        while i < len(clean_css):
            # Per review, check for `@media` at a rule boundary to avoid
            # matching it inside strings or other declarations. We also check
            # case-insensitively and handle more boundary types.
            k = i - 1
            is_at_boundary = (
                k < 0 or clean_css[k].isspace() or clean_css[k] in ("{", "}", ";")
            )

            current_slice = clean_css[i : i + 6].lower()
            if not (current_slice == "@media" and is_at_boundary):
                output.append(clean_css[i])
                i += 1
                continue

            try:
                brace_start = clean_css.index("{", i)
                brace_end = BookStyleContext._find_matching_brace_end(
                    clean_css,
                    brace_start,
                )
                if brace_end != -1:
                    i = brace_end  # Skip the entire @media block
                else:
                    # Unmatched brace; recover and continue.
                    i = BookStyleContext._recover_from_malformed_media_block(
                        clean_css,
                        i,
                    )
            except ValueError:
                # Malformed @media rule (e.g., no '{' or unmatched '{').
                # To avoid leaking partial rules, we advance the parser past
                # the likely end of this malformed block by finding the next
                # brace or newline.
                i = BookStyleContext._recover_from_malformed_media_block(clean_css, i)
        return "".join(output)

    def _harvest_layout_classes(self, css_text: str) -> None:
        """Parses CSS text to extract and store structural layout signatures.

        This method uses a simple regex-based parser and has known limitations.
        It does not support nested rules (other than `@media` which are stripped),
        attribute selectors (e.g., `[type="text"]`), or complex pseudo-classes
        and pseudo-elements. Its goal is to extract simple class-based style
        signatures, not to be a fully compliant CSS parser.

        By removing conditional `@media` blocks, we focus the analysis on the
        base styles, which is sufficient for identifying structural signatures.
        This is a safer approach than attempting to unwrap them with a single
        regex, which can fail on complex or malformed CSS.
        """
        clean_css = self._strip_css_media_blocks(css_text)
        i = 0
        iterations = 0
        while i < len(clean_css) and iterations < self._MAX_SCAN_ITERATIONS:
            iterations += 1

            # Advance past any trailing '}' or whitespace from the previous block
            # so that each raw_selectors slice cleanly corresponds to a single ruleset.
            while (
                i < len(clean_css)
                and iterations < self._MAX_SCAN_ITERATIONS
                and clean_css[i] in ("}", " ", "\t", "\n", "\r", "\f")
            ):
                i += 1
                iterations += 1

            if i >= len(clean_css):
                break

            i = self._process_css_rule(clean_css, i)

        if iterations >= self._MAX_SCAN_ITERATIONS and i < len(clean_css):
            log.warning(
                "CSS layout class harvesting aborted after reaching the iteration "
                "limit (%d). Remaining CSS length: %d",
                self._MAX_SCAN_ITERATIONS,
                len(clean_css) - i,
            )

    def _process_css_rule(self, clean_css: str, current_index: int) -> int:
        """Processes a single CSS rule from the given index.

        This helper parses a single rule block (selectors and declarations),
        identifies if it defines a significant layout style (float, indent,
        italic, bold), and if so, processes its selectors. It returns the index
        for the parser to continue from.

        Args:
            clean_css: The pre-cleaned CSS string to parse.
            current_index: The starting index for parsing the rule.

        Returns:
            The index in `clean_css` after the processed rule, or a new index
            for recovery if the rule is malformed.
        """
        try:
            brace_start = clean_css.index("{", current_index)
            brace_end = self._find_matching_brace_end(clean_css, brace_start)

            if brace_end == -1:
                # Malformed block, try to recover by skipping to the next
                # likely rule boundary.
                new_i = self._recover_from_malformed_media_block(
                    clean_css,
                    current_index,
                )
                return max(current_index + 1, new_i)  # Ensure progress

            raw_selectors = clean_css[current_index:brace_start]
            raw_declarations = clean_css[brace_start + 1 : brace_end - 1]

            selectors = raw_selectors.strip()
            if not selectors:
                return brace_end  # Ignore rules with no selectors

            declarations = raw_declarations.strip()
            is_float = self._is_float_declaration(declarations)
            is_indent, _ = self._is_indent_declaration(declarations)
            is_italic = self._is_italic_declaration(declarations)
            is_bold = self._is_bold_declaration(declarations)

            if is_float or is_indent or is_italic or is_bold:
                self._process_selector_group(
                    selectors,
                    is_float,
                    is_indent,
                    is_italic,
                    is_bold,
                )

            return brace_end
        except ValueError:
            # No more '{' found, parsing is complete.
            return len(clean_css)

    def _is_float_declaration(self, declarations: str) -> bool:
        """Checks if a CSS declaration block contains float or absolute/fixed positioning.

        Args:
            declarations: The property block of a CSS rule (e.g., "float: left;").

        Returns:
            True if the declarations contain a float property or absolute/fixed
            positioning, accounting for variations in casing and whitespace.

        Mutations:
            None.
        """
        # Use pre-compiled regexes for robust, case-insensitive matching that
        # correctly handles whitespace variations.
        return bool(
            self._FLOAT_DECL_RX.search(declarations)
            or self._POSITION_DECL_RX.search(declarations),
        )

    def _is_significant_indent(self, val: float, unit: str) -> bool:
        """Checks if an indent value meets the engine's significance threshold."""
        return (unit in {"em", "rem"} and val >= _MIN_INDENT_EM_REM) or (
            unit == "px" and val >= _MIN_INDENT_PX
        )

    def _is_indent_declaration(
        self,
        declarations: str,
    ) -> tuple[bool, re.Match[str] | None]:
        r"""Checks if a CSS declaration block specifies a significant indentation.

        Args:
            declarations: The property block of a CSS rule.

        Returns:
            True if a `margin-left` or `padding-left` property is found that
            meets the engine's significance threshold, along with the match
            object.

        Mutations:
            None.

        Rules & Logic:
            - Regex: `(?:margin|padding)-left\s*:\s*([0-9.]+)\s*(em|rem|px)`
            - Thresholds:
                - `val >= 1.5` for units `em` or `rem`.
                - `val >= 24` for unit `px`.
        """
        indent_match = self._INDENT_VALUE_RX.search(declarations)
        if not indent_match:
            return False, None
        val_str, unit = indent_match.group(1), indent_match.group(2).lower()
        try:
            val = float(val_str)
        except ValueError:
            # Defensive check against malformed values like '1.2.3'
            return False, None
        if self._is_significant_indent(val, unit):
            return True, indent_match
        return False, None

    def _is_italic_declaration(self, declarations: str) -> bool:
        """Checks if a CSS declaration block specifies italic font style.

        Args:
            declarations: The property block of a CSS rule.

        Returns:
            True if the declarations contain "font-style: italic".

        Mutations:
            None.
        """
        return bool(self._ITALIC_DECL_RX.search(declarations))

    def _is_bold_declaration(self, declarations: str) -> bool:
        """Checks if a CSS declaration block specifies a bold font weight.

        Args:
            declarations: The property block of a CSS rule.

        Returns:
            True if `font-weight` is "bold" or a numeric value of 600 or greater.

        Mutations:
            None.
        """
        return bool(self._BOLD_DECL_RX.search(declarations))

    def _process_selector_group(
        self,
        selectors: str,
        is_float: bool,
        is_indent: bool,
        is_italic: bool,
        is_bold: bool,
    ) -> None:
        """Processes a group of CSS selectors, mapping them to style compounds.

        For a given string of comma-separated selectors, this method extracts
        any class names (e.g., `.my-class`) and adds them as a `frozenset` to the
        appropriate compound sets (`floating_compounds`, etc.) based on the
        boolean flags provided.

        Args:
            selectors: The full selector string from a CSS rule.
            is_float: True if the rule is for floating elements.
            is_indent: True if the rule is for indented elements.
            is_italic: True if the rule is for italic elements.
            is_bold: True if the rule is for bold elements.
        """
        for selector_part in selectors.split(","):
            if compound := self._get_class_compound_from_selector(selector_part):
                self._add_compound_to_sets(
                    compound,
                    is_float,
                    is_indent,
                    is_italic,
                    is_bold,
                )

    def _get_class_compound_from_selector(
        self,
        selector_part: str,
    ) -> frozenset[str] | None:
        """Parses a selector part and returns a frozenset of its classes.

        This helper isolates the rightmost simple selector and extracts all class
        names, ignoring any pseudo-classes/elements.

        Args:
            selector_part: A single part of a comma-separated CSS selector.

        Returns:
            A frozenset of class names, or None if no classes are found.
        """
        if not (stripped_part := selector_part.strip()):
            return None

        # Per review, ignore complex selectors containing functions like `:is()`
        # or `:where()` to avoid mis-parsing. This is a conservative guard.
        if "(" in stripped_part or ")" in stripped_part:
            return None

        # Only consider classes from the rightmost simple selector, but ignore
        # pseudo-classes/elements when scanning for class names to avoid
        # over-generalizing compounds from contextual selectors.
        # We first isolate the rightmost *compound* by splitting on descendant/
        # child/sibling combinators, then scan only that chunk for classes.
        # This prevents selectors like `.a>.b` or `.a+.b` from being treated as
        # a single compound that contains both `.a` and `.b`.
        # Split on combinators and function boundaries to get candidate
        # compound chunks, then use the last non-empty chunk as the rightmost
        # compound.
        candidate_chunks = re.split(r"[\s>+~]+", stripped_part)
        # Filter out any empty chunks that may result from leading/trailing
        # combinators or extra whitespace.
        compound = ""
        for chunk in candidate_chunks[::-1]:
            if chunk := chunk.strip():
                compound = chunk
                break

        if not compound:
            return None

        # Strip pseudo-classes and pseudo-elements from the rightmost compound.
        # We only care about the structural part for class extraction.
        # e.g. `.c:hover::before` -> `.c`
        # The negative lookahead `(?![...])` prevents splitting on function-like
        # pseudo-classes (e.g., `:not()`), which are handled by the earlier
        # guard against parentheses.
        compound = re.split(r":(?![\\w-]+\()", compound)[0]

        if classes := re.findall(r"\.([\w-]+)", compound):
            return frozenset(classes)
        return None

    def _add_compound_to_sets(
        self,
        compound: frozenset[str],
        is_float: bool,
        is_indent: bool,
        is_italic: bool,
        is_bold: bool,
    ) -> None:
        """Adds a class compound to the appropriate style sets based on flags.

        Args:
            compound: A frozenset of class names from a CSS selector.
            is_float: True if the rule is for floating elements.
            is_indent: True if the rule is for indented elements.
            is_italic: True if the rule is for italic elements.
            is_bold: True if the rule is for bold elements.
        """
        if is_float:
            self.floating_compounds.add(compound)
        if is_indent:
            self.blockquote_compounds.add(compound)
        if is_italic:
            self.italic_compounds.add(compound)
        if is_bold:
            self.bold_compounds.add(compound)

    def _is_inside_tagged_container(
        self,
        node: Tag,
        tag_names: frozenset[str],
    ) -> bool:
        """Checks if a node or its ancestors match given tag or class names.

        This is a shared helper for `is_inside_code_block` and
        `is_inside_literal_code_tag`. It traverses up the DOM tree from the
        given node, checking for matching tag names or code-related CSS classes.

        Args:
            node: The BeautifulSoup `Tag` to start the search from.
            tag_names: A frozenset of tag names to check for.

        Returns:
            True if the node or any of its ancestors is a matching container.
        """
        for candidate in [node, *node.parents]:
            if isinstance(candidate, Tag):
                if candidate.name in tag_names:
                    return True
                class_attr = candidate.get("class")
                candidate_classes = set(coerce_class_list(class_attr))
                if not CODE_CLASSES.isdisjoint(candidate_classes):
                    return True
        return False

    def has_exact_layout_match(
        self,
        node: Tag,
        target_compounds: set[frozenset[str]],
    ) -> bool:
        """Checks if a node's classes are a superset of any target compound.

        This is the core matching logic. It determines if an element's `class`
        attribute contains all the classes required by at least one of the
        molecular signatures (`frozenset` of class names) in the target set.

        Args:
            node: The BeautifulSoup `Tag` to inspect.
            target_compounds: A set of frozensets, with each frozenset
                representing a required combination of class names.

        Returns:
            True if the node's classes match a compound; False otherwise.
        """
        class_attr = node.get("class")
        if not class_attr:
            return False
        # Only create the set if there are classes to check.
        node_classes = set(coerce_class_list(class_attr))
        return any(compound.issubset(node_classes) for compound in target_compounds)

    def is_floating_element(self, node: Tag) -> bool:
        """Checks if a node matches any registered floating element signature.

        Args:
            node: The BeautifulSoup `Tag` to inspect.

        Returns:
            True if the node's classes match a known floating compound.

        Mutations:
            None.
        """
        return self.has_exact_layout_match(node, self.floating_compounds)

    def is_blockquote_element(self, node: Tag) -> bool:
        """Checks if a node is a blockquote by tag name or CSS class.

        Args:
            node: The BeautifulSoup `Tag` to inspect.

        Returns:
            True if the node is a `<blockquote>` tag or if its classes match a
            known blockquote/indentation compound.

        Mutations:
            None.
        """
        if node.name == "blockquote":
            return True
        return self.has_exact_layout_match(node, self.blockquote_compounds)

    def is_italic_element(self, node: Tag) -> bool:
        """Checks if a node matches any registered italic element signature.

        Args:
            node: The BeautifulSoup `Tag` to inspect.

        Returns:
            True if the node's classes match a known italic compound.

        Mutations:
            None.
        """
        return self.has_exact_layout_match(node, self.italic_compounds)

    def is_bold_element(self, node: Tag) -> bool:
        """Checks if a node matches any registered bold element signature.

        Args:
            node: The BeautifulSoup `Tag` to inspect.

        Returns:
            True if the node's classes match a known bold compound.

        Mutations:
            None.
        """
        return self.has_exact_layout_match(node, self.bold_compounds)

    def is_inside_code_block(self, node: Tag) -> bool:
        """Checks if a node is inside a technical code container (`<pre>` or `<code>`).

        This method provides a defensive shield to prevent normalizers from
        mutating content within code blocks. It traverses up the DOM tree from
        the given node, checking both tag names and a list of common code-related
        CSS classes.

        Args:
            node: The BeautifulSoup `Tag` to start the search from.

        Returns:
            True if the node or any of its ancestors is a code container.

        Mutations:
            None.

        Rules & Logic:
            - Tag names checked: `pre`, `code`.
            - Classes checked: `programlisting`, `code-snippet`, `source-code`.
        """
        return self._is_inside_tagged_container(node, frozenset(["pre", "code"]))

    def is_inside_literal_code_tag(self, node: Tag) -> bool:
        """Checks if a node is inside a literal `<code>` tag or equivalent class.

        This is a more surgical version of `is_inside_code_block`. It
        specifically targets `<code>` tags and their class-based equivalents,
        but intentionally ignores `<pre>` tags. This allows normalizers to
        process content within `<pre>` blocks (like spacer tables) while still
        protecting inline `<code>` snippets.

        Args:
            node: The BeautifulSoup `Tag` to start the search from.

        Returns:
            True if the node or any of its ancestors is a `<code>` container.

        Mutations:
            None.

        Rules & Logic:
            - Tag names checked: `code`.
            - Classes checked: `programlisting`, `code-snippet`, `source-code`.
        """
        return self._is_inside_tagged_container(node, frozenset(["code"]))

    def normalize_inline_floats(self, node: Tag) -> bool:
        """Promotes an inline `style` with float/position to a canonical class.

        If a node has an inline style attribute that signifies a float or overlay
        (e.g., `float:`, `position: absolute`, `position: fixed`), this method
        adds the `floating-element` class to the node's class list. This
        standardizes floating elements for easier detection by `is_floating_element`.

        Args:
            node: The BeautifulSoup `Tag` to inspect and potentially modify.

        Returns:
            True if the node was modified, False otherwise.

        Mutations:
            Modifies the `class` attribute of the input `node` in-place if an
            inline float/overlay style is found and the canonical class is not present.
        """
        style_str = normalize_style_attribute(node.get("style"))
        if not style_str:
            return False
        # Reuse the same detection rules as CSS-based float/overlay parsing so
        # inline styles are classified consistently.
        # Per review, the regexes in `_is_float_declaration` are confirmed to be
        # robust against whitespace and case variations, making them compatible
        # with the simple string stripping performed by `normalize_style_attribute`.
        if self._is_float_declaration(style_str):
            classes_list = coerce_class_list(node.get("class"))
            if FLOATING_ELEMENT_CLASS not in classes_list:
                classes_list.append(FLOATING_ELEMENT_CLASS)
                node["class"] = " ".join(classes_list)
                return True
        return False

    def normalize_inline_indents(self, node: Tag) -> bool:
        """Promotes an inline `style` with significant indentation to a canonical class.

        If a node has an inline style with `margin-left` or `padding-left` that
        meets the engine's threshold, this method adds the `blockquote-element`
        class to the node's class list. This standardizes indented elements for
        easier detection by `is_blockquote_element`.
        Args:
            node: The BeautifulSoup `Tag` to inspect and potentially modify.

        Returns:
            True if the node was modified, False otherwise.

        Mutations:
            Modifies the `class` attribute of the input `node` in-place if a
            significant inline indent style is found and the canonical class is
            not present.
        """
        style_str = normalize_style_attribute(node.get("style"))
        if not style_str:
            return False
        # Reuse the same detection rules as CSS-based indent parsing to keep logic
        # centralized and avoid duplicating threshold checks.
        is_indent, indent_match = self._is_indent_declaration(style_str)
        if is_indent and indent_match:
            classes_list = coerce_class_list(node.get("class"))
            if BLOCKQUOTE_ELEMENT_CLASS not in classes_list:
                classes_list.append(BLOCKQUOTE_ELEMENT_CLASS)
                node["class"] = " ".join(classes_list)

                val_str = indent_match.group(1)
                # Preserve the raw numeric string to maintain precision.
                # Per review, namespace the attribute to avoid clobbering.
                node["data-dn-indent-level"] = val_str

                return True
        return False
