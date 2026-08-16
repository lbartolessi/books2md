"""A format normalization engine for mathematical expressions.

This module operates as a Stage 2 processor. Its primary function is to
normalize various representations of mathematical content (MathML, LaTeX in
image attributes) into a consistent, Pandoc-compatible format. This ensures
that mathematical expressions are both visually preserved and semantically
structured for downstream processing by RAG and LLM systems.

The processor handles two main cases:
1.  **Pure MathML (`<math>` tags):** Converts MathML into LaTeX strings using
    an XSLT transformation and wraps them in appropriate `<div>` or `<span>`
    tags formatted for Pandoc.
2.  **Hybrid Images (`<img>`, `<svg>`):** Enriches images that have LaTeX
    metadata in their attributes by creating a container that includes both the
    visual image and its corresponding LaTeX representation.

This processor must run after `structural_sanitizer` to ensure that layout
styles have been promoted to classes, which helps in determining whether a
mathematical element is block-level or inline.

Analytical Blueprint:
---------------------

Based on the specification, the following logic will be mapped to the class
methods:

- __init__: Initializes telemetry counters and handles the conditional import
  of `lxml` for XSLT transformations.
- process: Orchestrates the normalization pipeline, executing the processing
  of MathML tags and hybrid images in a strict order.
- _extract_latex_from_attributes: Extracts LaTeX strings from image attributes
  (`data-latex`, `data-math`, `alt`) based on a priority order.
- _transform_mathml_to_latex: Converts a MathML tag to a LaTeX string using a
  pre-loaded XSLT stylesheet.
- _is_block_level: Determines if a math-related tag should be treated as
  block-level or inline based on its context in the DOM.
- _process_math_tags: Finds and converts all `<math>` tags in the document.
- _process_hybrid_images: Finds and wraps all `<img>` and `<svg>` tags that
  contain LaTeX metadata.
"""

import importlib
import logging
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any, Final

from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString

from .core import BookStyleContext, PipelineStatus
from .core.dom_utils import (
    BLOCK_LEVEL_TAGS,
    find_all_snapshot,
    generate_processor_metadata,
)

log = logging.getLogger(__name__)

# Conditional import of lxml for XSLT transformations.
try:
    _ETREE_MODULE = importlib.import_module("lxml.etree")
    LXML_AVAILABLE = True
    _LXML_ERROR_CLASS = _ETREE_MODULE.LxmlError
except ImportError:
    LXML_AVAILABLE = False
    _ETREE_MODULE = None  # Placeholder for type hinting
    _LXML_ERROR_CLASS = Exception  # Fallback if lxml is not available

_MATH_RELATED_TAGS: Final[frozenset[str]] = frozenset(
    {
        "math",
        "img",
        "svg",
    },
)


class MathProcessor:
    """A format normalization engine for mathematical expressions.

    This processor normalizes various representations of mathematical content
    (MathML, LaTeX in image attributes) into a consistent, Pandoc-compatible
    format. It ensures that mathematical expressions are both visually preserved
    and semantically structured for downstream processing.

    Attributes:
        LATEX_ALT_VALIDATION_TOKENS (tuple[str, ...]): LaTeX tokens used to validate
            if an `alt` attribute contains a mathematical expression.
        MIN_LATEX_LENGTH (int): The minimum character length for a string to be
            considered valid LaTeX.
        context (BookStyleContext): The shared context for the book.
        equations_converted (int): A counter for pure MathML expressions converted to LaTeX.
        hybrid_blocks_created (int): A counter for hybrid blocks (image + LaTeX) created.
        lxml_available (bool): A flag indicating if the `lxml` library is available.
        xslt_transformer (Any | None): The compiled XSLT transformer object for
            MathML-to-LaTeX conversion, if available.
    """

    # LaTeX structural tokens for validating 'alt' attribute content.
    LATEX_ALT_VALIDATION_TOKENS: Final[tuple[str, ...]] = (
        r"\frac",
        r"\int",
        r"\alpha",
        r"^{",
        r"_{",
        r"\vec",
        r"\sum",
    )
    # Minimum character length for a string to be considered valid LaTeX.
    MIN_LATEX_LENGTH: Final[int] = 3

    def __init__(self, context: BookStyleContext) -> None:
        """Initializes the math processor and its dependencies.

        This constructor sets up telemetry counters and handles the conditional
        import of the `lxml` library, which is required for MathML-to-LaTeX
        XSLT transformations. If `lxml` is not available, this capability is
        disabled, and a warning is logged.

        Args:
            context (BookStyleContext): The shared context for the book.

        Raises:
            FileNotFoundError: If the XSLT stylesheet is not found at its expected path.
            Exception: Propagates any unexpected error during XSLT initialization.

        Mutations:
            - Initializes `self.equations_converted` and `self.hybrid_blocks_created` to 0.
            - Sets `self.lxml_available` to `True` or `False` based on import success.
            - Sets `self.xslt_available` and `self.xslt_transformer` based on the
              result of `_initialize_xslt_transformer`.

        Rules & Limits:
            - lxml Dependency: The `lxml` library is an optional dependency. If it
              cannot be imported, a warning MUST be logged, and the MathML-to-LaTeX
              conversion capability (Case B) MUST be disabled for the processor's
              lifecycle.
            - Instance Lifecycle: Assumes this instance is scoped to a single book,
              per Global Directive #3.

        Calls:
            - `_initialize_xslt_transformer`: To load and compile the XSLT stylesheet.
        """
        self.context = context
        self.equations_converted: int = 0
        self.hybrid_blocks_created: int = 0
        self.lxml_available = LXML_AVAILABLE
        # Indicates whether the MathML-to-LaTeX XSLT stylesheet is present and usable.
        self.xslt_available: bool = False
        self.xslt_transformer: Any | None = None
        self.xslt_available, self.xslt_transformer = self._initialize_xslt_transformer()

    def _initialize_xslt_transformer(self) -> tuple[bool, Any | None]:
        """Loads and compiles the XSLT transformer for MathML to LaTeX conversion.

        This helper encapsulates the logic for finding, parsing, and compiling
        the XSLT stylesheet. It handles all exceptions related to file access
        and parsing, logging them appropriately and returning a clear status.

        Returns:
            A tuple containing:
            - bool: True if the transformer was successfully initialized, False otherwise.
            - Any | None: The compiled lxml.etree.XSLT object, or None on failure.
        """
        if not (self.lxml_available and _ETREE_MODULE):
            return False, None

        xslt_parse_error = getattr(_ETREE_MODULE, "XSLTParseError", OSError)
        xslt_loading_exceptions = (FileNotFoundError, OSError)
        xslt_parsing_exceptions = (xslt_parse_error,)
        xslt_path: Path | None = None
        try:
            xslt_path = Path(__file__).parent / "resources/mml-to-latex.xsl"
            if not xslt_path.exists():
                log.warning(
                    "MathML-to-LaTeX XSLT stylesheet not found at %s; "
                    "MathML conversion will be skipped for this run.",
                    xslt_path,
                )
                return False, None

            parser = _ETREE_MODULE.XMLParser(resolve_entities=False, no_network=True)
            xslt_doc = _ETREE_MODULE.parse(str(xslt_path), parser)
            transformer = _ETREE_MODULE.XSLT(xslt_doc)
            return True, transformer
        except xslt_parsing_exceptions as e:
            log.critical(
                "Failed to parse XSLT stylesheet at %s: %s",
                xslt_path,
                e,
                exc_info=True,
            )
        except xslt_loading_exceptions as e:
            log.critical(
                "Failed to load XSLT stylesheet from %s: %s",
                xslt_path,
                e,
                exc_info=True,
            )
        except Exception as e:
            log.critical(
                "An unexpected error occurred during XSLT initialization: %s",
                e,
                exc_info=True,
            )
            raise
        return False, None

    def _find_and_validate_raw_latex(self, tag: Tag) -> tuple[str, str] | None:
        """Searches for LaTeX content in tag attributes and performs initial validation.

        This helper method iterates through a predefined list of attributes
        (`data-latex`, `data-math`, `alt`, `title`) in priority order. It
        extracts the raw string value, normalizes it, and performs a basic
        length check.

        Args:
            tag: The `<img>` or `<svg>` tag to inspect.

        Returns:
            A tuple `(latex_string, source_attribute_name)` if a valid LaTeX
            string meeting the minimum length requirement is found, otherwise `None`.

        Rules & Limits:
            - Attribute Priority: The search order is strictly: `data-latex`,
              `data-math`, `alt`, `title`.
            - Minimum Length: The extracted string must be at least
              `self.MIN_LATEX_LENGTH` characters long.
            - Normalization: Attribute values are normalized to strings and stripped
              of leading/trailing whitespace.
        """
        candidate_attrs = ("data-latex", "data-math", "alt", "title")
        for attr in candidate_attrs:
            if value := tag.get(attr):
                if isinstance(value, list):
                    value = " ".join(str(v) for v in value)
                if (
                    isinstance(value, str)
                    and (stripped := value.strip())
                    and len(stripped) >= self.MIN_LATEX_LENGTH
                ):
                    return stripped, attr
        return None

    def _extract_latex_from_attributes(self, tag: Tag) -> str | None:
        r"""Extracts a LaTeX string from an image tag's attributes.

        This method searches for LaTeX content within the attributes of an `<img>`
        or `<svg>` tag, normalizes it, and performs sanity checks to avoid
        creating empty or malformed math wrappers around non-math content.

        Args:
            tag: The `<img>` or `<svg>` tag to inspect.

        Returns:
            A cleaned and validated LaTeX string, or `None` if no suitable
            LaTeX content is found.
        Mutations:
            None.

        Rules & Limits:
            - Initial Extraction: Delegates to `_find_and_validate_raw_latex` to
              find the raw LaTeX string based on attribute priority and minimum length.
            - Strict `alt`/`title` Validation: The value from `alt` or `title` is
              only considered valid if it contains at least one of the tokens
              defined in `LATEX_ALT_VALIDATION_TOKENS` OR if it passes a
              `_looks_like_simple_latex` heuristic.
            - Return Value: The first non-empty, validated value found is stripped
              of whitespace and returned. If no attribute yields a valid string
              `None` is returned.
            - Node Type Safety: Expects a `Tag` object. Behavior on a `NavigableString`
              would result in `None` as it has no attributes.
        """
        found_latex = self._find_and_validate_raw_latex(tag)
        if not found_latex:
            return None

        latex_raw, source_attr = found_latex

        # For 'alt' and 'title', require at least one LaTeX-like character.
        if source_attr in ("alt", "title"):
            # First, apply strict token-based validation using configured tokens.
            lacks_configured_tokens = all(
                token not in latex_raw for token in self.LATEX_ALT_VALIDATION_TOKENS
            )

            # If strict tokens are missing, try a secondary, lighter heuristic.
            if lacks_configured_tokens and not self._looks_like_simple_latex(latex_raw):
                return None

        # Prefer explicit math attributes in a stable order.
        return latex_raw

    def _looks_like_simple_latex(self, text: str) -> bool:
        """Heuristic to detect simple LaTeX without configured validation tokens.

        This is intentionally lightweight and focuses on common inline LaTeX cues
        such as superscripts, subscripts, and commands, so that short expressions
        like `$x$`, `y^2`, or `E=mc^2` are not rejected solely because they don't
        contain any of `LATEX_ALT_VALIDATION_TOKENS`.

        Args:
            text: The string to evaluate for simple LaTeX patterns.

        Returns:
            True if the text contains simple LaTeX cues, False otherwise.
        """
        return any(cue in text for cue in ("\\", "^", "_", "$")) if text else False

    def _convert_bs4_to_lxml(self, bs4_tag: Tag) -> Any | None:
        """Converts a BeautifulSoup Tag to an lxml element for processing.

        This helper uses a secure parser to convert a BeautifulSoup tag into an
        lxml element, which is required for XSLT transformations. The calling
        method is responsible for handling any parsing exceptions.

        Args:
            bs4_tag: The BeautifulSoup Tag to convert.

        Returns:
            An lxml element object if lxml is available, otherwise None.
        """
        if not _ETREE_MODULE:
            return None
        # Do NOT mutate the original BeautifulSoup math_tag with xmlns.
        # Instead, ensure the lxml element has the correct namespace for XSLT.
        mathml_str = str(bs4_tag)
        parser = _ETREE_MODULE.XMLParser(resolve_entities=False, no_network=True)
        # The fromstring call is intentionally not in a try-except block here,
        # as the calling method (_transform_mathml_to_latex) handles exceptions.
        return _ETREE_MODULE.fromstring(mathml_str.encode("utf-8"), parser)

    def _ensure_lxml_namespace(self, lxml_doc: Any) -> Any:
        """Ensures an lxml element has the MathML namespace for XSLT processing.

        If the root element is 'math' and doesn't have the MathML namespace,
        this method creates a new lxml element with the correct namespace and
        copies the children, leaving the original element untouched.

        Args:
            lxml_doc: The lxml element to check.

        Returns:
            The lxml element, potentially a new one with the correct namespace.
        """
        if (
            _ETREE_MODULE
            and lxml_doc.tag == "math"
            and lxml_doc.nsmap.get(None) != "http://www.w3.org/1998/Math/MathML"
        ):
            new_lxml_doc = _ETREE_MODULE.Element(
                "{http://www.w3.org/1998/Math/MathML}math",
                nsmap={None: "http://www.w3.org/1998/Math/MathML"},
                attrib=lxml_doc.attrib,  # Preserve attributes
            )
            new_lxml_doc.text = lxml_doc.text  # Preserve text content
            new_lxml_doc.tail = lxml_doc.tail  # Preserve tail content
            for child in lxml_doc:
                new_lxml_doc.append(child)
            return new_lxml_doc
        return lxml_doc

    def _transform_mathml_to_latex(self, math_tag: Tag) -> str | None:
        """Converts a MathML DOM tree to a LaTeX string using XSLT.

        This method applies a pre-loaded XSLT stylesheet to transform a `<math>`
        tag and its contents into a plain text LaTeX representation.

        Args:
            math_tag: The `<math>` tag containing the MathML to be converted.

        Returns:
            The resulting LaTeX string if the transformation is successful,
            or `None` if an error occurs.

        Mutations:
            None.

        Rules & Limits:
            - Precondition: This method should only be called if `self.lxml_available`
              and `self.xslt_transformer` are not `None`.
            - Secure XML Parsing: The MathML string must be parsed using a secure
              `lxml` parser configured with `resolve_entities=False` and
              `no_network=True` to prevent XXE vulnerabilities.
            - Error Handling: If any `lxml` exception occurs during parsing or
              transformation, a warning MUST be logged using the `logging` module,
              and the function must return `None`.
        """
        if not (self.lxml_available and self.xslt_available):
            # Avoid flooding logs for documents with many <math> tags; rely on
            # initialization-time warnings to surface configuration issues.
            log.debug(
                "Skipping MathML to LaTeX conversion: lxml or XSLT stylesheet is not available.",
            )
            return None
        return self._apply_xslt_transform(math_tag)

    def _apply_xslt_transform(self, math_tag: Tag) -> str | None:
        """Applies the XSLT transformation to a single MathML tag.

        This helper encapsulates the core transformation logic, including the
        conversion from BeautifulSoup to lxml, namespace handling, and the
        actual XSLT processing. It is designed to be called only after
        pre-conditions (like lxml availability) have been checked.

        Args:
            math_tag: The BeautifulSoup `<math>` tag to transform.

        Returns:
            The resulting LaTeX string if successful, otherwise None.
        """
        try:
            lxml_math_doc = self._convert_bs4_to_lxml(math_tag)
            if lxml_math_doc is None:
                log.warning(
                    "Failed to convert BeautifulSoup tag to lxml element for MathML processing.",
                )
                return None

            lxml_math_doc = self._ensure_lxml_namespace(lxml_math_doc)
            # xslt_transformer is guaranteed to be non-None if xslt_available is True.
            assert self.xslt_transformer is not None, (
                "XSLT transformer should not be None if xslt_available is True."
            )
            latex_result = self.xslt_transformer(lxml_math_doc)  # type: ignore [operator]
            return str(latex_result).strip()
        except _LXML_ERROR_CLASS as e:  # pylint: disable=broad-except
            log.warning(
                "lxml error during MathML to LaTeX transformation for tag '%s': %s",
                str(math_tag)[:100],
                e,
            )
            return None

    def _is_only_significant_content(self, parent: Tag, tag: Tag) -> bool:
        """Checks if a tag is the only significant content within its parent.

        "Significant content" is defined as any non-whitespace text node or any
        other tag.

        Args:
            parent: The parent tag to inspect.
            tag: The child tag to check for exclusivity.

        Returns:
            True if `tag` is the only significant content in `parent`, False otherwise.
        """
        for child in parent.contents:
            if child is tag:
                continue
            if isinstance(child, NavigableString) and child.strip():
                return False  # It's inline because there's other text
            if isinstance(child, Tag):
                return False  # It's inline because there's another tag
        return True

    def _is_block_level(self, tag: Tag) -> bool:
        """Determines if a tag should be treated as block-level or inline.

        This heuristic is used to decide whether to wrap a mathematical element
        in a `<div>` (block) or a `<span>` (inline).

        Args:
            tag: The tag to evaluate (e.g., `<math>`, `<img>`).

        Returns:
            `True` if the tag is determined to be block-level, `False` if inline.
        Mutations:
            None.

        Rules & Limits:
            - A tag is considered **block-level** if:
              1. It is a `<math>`, `<img>`, or `<svg>` tag and its immediate parent is a `<p>` tag
                 that contains no other significant text content besides the
                 tag itself.
            - All other cases are considered **inline**. This includes cases where the parent is an inline-like HTML tag
              (e.g., `<span>`, `<em>`) or a block-like tag that shares content with the math element.
            - Node Type Safety: Expects a `Tag`. Behavior is undefined for a
              `NavigableString`. A `None` parent will be handled gracefully.
        """
        parent = tag.parent
        if not parent:
            return True  # Treat as block if no parent (e.g., root element)

        parent_name = parent.name or ""

        # If the parent is not a known block-like container (e.g., <span>, <em>, <strong>),
        # then the math element should be treated as inline to avoid disrupting inline flow.
        if parent_name not in BLOCK_LEVEL_TAGS:
            return False

        # If the parent is a known block-like container (e.g., <div>, <li>, <td>)
        # AND it's not a <p>, then the math element is considered block-level
        # as per the spec's rule 1 ("Its immediate parent is not a <p> tag", refined).
        # This means display math in a <div> or <li> will be block-level.
        if parent_name != "p":
            return True

        # If the parent is a <p> tag, apply the "only significant content" rule.
        # This rule applies only to math-related tags.
        if tag.name not in _MATH_RELATED_TAGS:
            return False  # Default to inline if not a math-related tag

        return self._is_only_significant_content(parent, tag)

    def _process_single_math_tag(self, math_tag: Tag, soup: BeautifulSoup) -> bool:
        """Processes a single MathML tag, converting it to LaTeX and wrapping it.

        This helper function encapsulates the logic for transforming a single
        `<math>` tag. It handles LaTeX conversion, content validation, block/inline
        determination, and DOM mutation.

        Args:
            math_tag: The `<math>` tag to process.
            soup: The root BeautifulSoup object, used as a factory for new tags.

        Returns:
            True if the tag was successfully processed and mutated, False otherwise.
        """
        if self.context.is_inside_code_block(math_tag):
            return False

        latex_str = self._transform_mathml_to_latex(math_tag)
        if not latex_str:
            return False

        # For MathML conversions, apply a check for meaningful content.
        # We want to filter out empty/meaningless strings while preserving
        # valid operator-only LaTeX (e.g., \cdots, \pm, \equiv).
        stripped_latex = latex_str.strip()
        if not stripped_latex:
            log.warning(
                "MathML conversion resulted in empty/whitespace-only LaTeX: '%s'",
                latex_str,
            )
            return False

        is_block = self._is_block_level(math_tag)
        wrapper_class = "math-block" if is_block else "math-inline"
        # Do not inject extra spaces inside delimiters to preserve formatting.
        formatted_latex = f"$${stripped_latex}$$" if is_block else f"${stripped_latex}$"
        wrapper_tag = soup.new_tag(
            "div" if is_block else "span",
            attrs={"class": wrapper_class},
        )
        wrapper_tag.string = formatted_latex
        parent = math_tag.parent
        if (
            is_block
            and parent
            and parent.name == "p"
            and self._is_only_significant_content(parent, math_tag)
        ):
            # If the math tag is the only significant content in a <p>, replace the
            # entire paragraph to maintain block-level semantics.
            parent.replace_with(wrapper_tag)
        else:
            math_tag.replace_with(wrapper_tag)
        self.equations_converted += 1
        return True

    def _yield_math_tag_candidates(self, soup: BeautifulSoup) -> Iterator[Tag]:
        """Yields <math> tags that are candidates for processing.

        This generator separates the traversal and initial filtering of <math>
        tags from the mutation logic. It finds all <math> tags in the document.

        Args:
            soup: The BeautifulSoup object to search within.

        Yields:
            Tag: A BeautifulSoup Tag object for each <math> element found.
        """
        if not self.lxml_available:
            return
        for math_tag in find_all_snapshot(soup, "math"):
            if isinstance(math_tag, Tag):
                yield math_tag

    def _process_math_tags(self, soup: BeautifulSoup) -> bool:
        """Finds and converts all MathML tags (Case B) in the document.

        This method iterates through candidate `<math>` tags yielded by a generator
        and delegates the transformation of each to a helper method.

        Args:
            soup: The in-memory DOM of the document.

        Returns:
            `True` if at least one `<math>` tag was successfully processed
            and mutated, `False` otherwise.
        Mutations:
            - Replaces `<math>` tags with new `<div class="math-block">` or
              `<span class="math-inline">` tags.
            - Increments `self.equations_converted` for each successful conversion.

        Rules & Limits:
            - Precondition: This process is skipped entirely if `lxml` is not available.
            - Code Shield: Bypasses any `<math>` tag for which
              `self.context.is_inside_code_block()` returns `True`.
            - Formatting:
                - Block-level equations are wrapped in `$$...$$`.
                - Inline equations are wrapped in `$ ... $`.
            - DOM Creation: New tags MUST be created using `soup.new_tag` with the
              `attrs` dictionary (e.g., `attrs={'class': 'math-block'}`).
            - Full depth traversal: Yes.
        """
        made_changes = False
        for math_tag in self._yield_math_tag_candidates(soup):
            if self._process_single_math_tag(math_tag, soup):
                made_changes = True

        return made_changes

    def _yield_hybrid_image_candidates(
        self,
        soup: BeautifulSoup,
    ) -> Iterator[tuple[Tag, str]]:
        """Yields <img> and <svg> tags that are candidates for hybrid processing.

        This generator finds all image-like tags, applies the Code Shield guard,
        and extracts LaTeX from their attributes. It yields a tuple of the tag
        and its associated LaTeX string for each valid candidate.

        Args:
            soup: The BeautifulSoup object to search within.

        Yields:
            A tuple containing the candidate Tag and its extracted LaTeX string.
        """
        for img_tag in find_all_snapshot(soup, ["img", "svg"]):
            if not isinstance(img_tag, Tag) or self.context.is_inside_code_block(
                img_tag,
            ):
                continue
            if latex_str := self._extract_latex_from_attributes(img_tag):
                yield img_tag, latex_str

    def _process_single_hybrid_image(
        self,
        img_tag: Tag,
        latex_str: str,
        soup: BeautifulSoup,
    ) -> None:
        """Processes a single hybrid image, wrapping it and adding its LaTeX.

        This helper contains the mutation logic for a single hybrid image. It
        determines if the image is block or inline, creates the appropriate
        wrapper, and appends both the image and its LaTeX representation.

        Args:
            img_tag: The <img> or <svg> tag to process.
            latex_str: The pre-validated LaTeX string associated with the tag.
            soup: The root BeautifulSoup object for creating new tags.
        """
        if self._is_block_level(img_tag):
            wrapper_tag = soup.new_tag("div", attrs={"class": "math-block"})
            formatted_latex = f"$${latex_str}$$"
            parent = img_tag.parent
            # If the image is the only significant content in a <p>, replace the
            # entire paragraph to maintain block-level semantics and avoid
            # leaving behind an empty <p> tag.
            if (
                parent
                and parent.name == "p"
                and self._is_only_significant_content(parent, img_tag)
            ):
                wrapper_tag.append(img_tag)
                parent.replace_with(wrapper_tag)
            else:
                img_tag.replace_with(wrapper_tag)
                wrapper_tag.append(img_tag)
        else:
            wrapper_tag = soup.new_tag("span", attrs={"class": "math-inline"})
            formatted_latex = f"${latex_str}$"
            img_tag.wrap(wrapper_tag)

        wrapper_tag.append(NavigableString(formatted_latex))
        self.hybrid_blocks_created += 1

    def _process_hybrid_images(self, soup: BeautifulSoup) -> bool:
        """Finds and wraps all hybrid math images (Case C) in the document.

        This method iterates through candidate `<img>` and `<svg>` tags yielded
        by a generator and delegates the transformation of each to a helper method.

        Args:
            soup: The in-memory DOM of the document.

        Returns:
            `True` if at least one hybrid image was successfully processed
            and mutated, `False` otherwise.

        Mutations:
            - Wraps `<img>` or `<svg>` tags (and sometimes their parent `<p>`) with
              new `<div class="math-block">` or `<span class="math-inline">` tags.
            - The original image and the new LaTeX text node are moved inside the wrapper.
            - Increments `self.hybrid_blocks_created` for each successful wrapping.

        Rules & Limits:
            - Target Tags: `<img>`, `<svg>`.
            - Code Shield: Bypasses any tag for which
              `self.context.is_inside_code_block()` returns `True`.
            - Case A Bypass: If `_extract_latex_from_attributes` returns an empty
              string, the tag is ignored (pass-through).
            - Block-level `<p>` Replacement: If a block-level image's parent is a
              `<p>`, the entire `<p>` tag is replaced by the new `<div>`, and the
              image is moved inside it.
            - DOM Creation: New tags MUST be created using `soup.new_tag` with the
              `attrs` dictionary.
            - Full depth traversal: Yes.
        """
        made_changes = False
        for img_tag, latex_str in self._yield_hybrid_image_candidates(soup):
            self._process_single_hybrid_image(img_tag, latex_str, soup)
            made_changes = True

        return made_changes

    def process(self, soup: BeautifulSoup) -> tuple[BeautifulSoup, Mapping[str, Any]]:
        """Executes the full math normalization pipeline on the document.

        This is the main entry point for the processor. It orchestrates the
        conversion of pure MathML and the wrapping of hybrid image-based
        equations in a strict order.

        Args:
            soup: The in-memory DOM of the document to be processed.

        Returns:
            A tuple containing the mutated soup object and a metadata dictionary.

        Mutations:
            - The input `soup` object is modified in-place by the `_process_*`
              helper methods.

        Rules & Limits:
            - Pipeline Order: This processor must run after `table_normalizer` and
              `blockquote_processor`.
            - Internal Execution Order:
              1. `_process_math_tags(soup)`
              2. `_process_hybrid_images(soup)`
            - Status Logic: The final status is 'success' if the sum of
              `equations_converted` and `hybrid_blocks_created` is greater than 0.
              Otherwise, the status is 'idle'.
            - Output Metadata Contract: The returned dictionary must be nested under
              the key `math_processing` and contain `equations_normalized`,
              `hybrid_blocks_structured`, `status`, and `execution_timestamp`.
        """
        # Case B: Process pure MathML tags
        changes_b = self._process_math_tags(soup)

        # Case C: Process hybrid images with LaTeX metadata
        changes_c = self._process_hybrid_images(soup)

        has_changes = changes_b or changes_c
        status = PipelineStatus.SUCCESS if has_changes else PipelineStatus.SUCCESS_NOOP

        metadata = generate_processor_metadata(
            processor_key="math_processing",
            status=status,
            equations_normalized=self.equations_converted,
            hybrid_blocks_structured=self.hybrid_blocks_created,
        )
        return soup, metadata
