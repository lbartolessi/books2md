"""A semantic micro-normalizer for healing and realigning heading hierarchies.

This module executes as a Stage 2 processor, responsible for enforcing a mathematically
valid and continuous heading structure (`<h1>` through `<h6>`) across one or more
document assets. It operates in three distinct passes: first, it promotes styled
paragraphs to semantic headings; second, it demotes headings that violate
structural rules; and third, it levels the remaining hierarchy to repair
non-contiguous jumps.

This processor must run after Stage 1 sanitization and before any block-level
partitioning to ensure a clean semantic tree for downstream modules.

Analytical Blueprint:
---------------------

Based on the specification, the following logic will be mapped to the class methods:

Global Free Functions (Module Level):
    - None present in the skeleton.

Class Methods (HeadingNormalizer):
    - __init__: Initializes telemetry counters (`headings_promoted`, `headings_demoted`,
      `hierarchy_fixes`) and the cross-file state variable `self._current_level`.
    - process: Orchestrates the three-pass normalization (promotion, demotion,
      and hierarchy fixing). The code block immunity protocol is applied on a
      per-node basis within each pass.
    - _promote_styled_paragraphs: Implements the promotion pass. It finds
      non-semantic elements styled as headings (e.g., bold paragraphs, elements
      with specific classes, or ARIA roles) and promotes them to the corresponding
      `h1`-`h6` tags. It delegates to specific helper methods for each promotion type.
    - _demote_invalid_headings: Implements the demotion pass. It scans all `h1`-`h6`
      tags and demotes those that violate structural rules (e.g., excessive length,
      high link-to-text ratio) to `<p>` tags.
    - _fix_hierarchy: Implements the hierarchy correction pass. It traverses all
      remaining `h1`-`h6` tags, using `self._current_level` to enforce continuity
      and correct any non-contiguous level jumps.
    - get_metadata: Compiles and returns the final processing metadata, nested under
      the `heading_normalization` key and conforming to the standard output contract.
"""

import logging
import re
from collections import defaultdict
from collections.abc import Mapping
from typing import Any, cast

from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString, PageElement

from .core import BookStyleContext, PipelineStatus
from .core.dom_utils import (
    coerce_class_list,
    find_all_snapshot,
    generate_processor_metadata,
    is_ignorable_node,
)

log = logging.getLogger(__name__)


# --- Module-level Constants and Pre-compiled Regexes ---
MIN_HEADING_LEVEL: int = 1
MAX_HEADING_LEVEL: int = 6
VALID_HEADING_TAGS: frozenset[str] = frozenset(
    f"h{i}" for i in range(MIN_HEADING_LEVEL, MAX_HEADING_LEVEL + 1)
)
# Pre-compiled regex for matching valid heading tags (e.g., h1-h6).
HEADING_TAG_RX: re.Pattern[str] = re.compile(
    rf"^h[{MIN_HEADING_LEVEL}-{MAX_HEADING_LEVEL}]$",
)
# Pre-compiled regex for validating CSS class names that don't require escaping.
# This ensures class names are safe to use in CSS selectors without escaping.
_VALID_CSS_CLASS_RX: re.Pattern[str] = re.compile(r"^[a-zA-Z_][\w-]*$")


class _DemotionStrategy:
    """Encapsulates the logic for determining if a heading should be demoted.

    This strategy object holds the configuration thresholds and provides methods
    to evaluate a heading against these thresholds.
    """

    def __init__(self, hn_config: _HeadingNormalizerConfig) -> None:
        """Initializes the demotion strategy with the heading normalizer's configuration."""
        self.hn_config = hn_config

    def should_demote_by_length(self, heading_text_len: int) -> bool:
        """Checks if a heading should be demoted due to its length."""
        return heading_text_len > self.hn_config.max_heading_length

    def should_demote_by_link_density(
        self,
        heading: Tag,
        heading_text_len: int,
    ) -> bool:
        """Checks if a heading should be demoted due to its link density."""
        links = heading.find_all("a")
        if not links:
            return False
        link_text_len = sum(len(a.get_text(strip=True)) for a in links)
        # Avoid division by zero, though heading_text_len is checked before.
        if heading_text_len == 0:
            return False
        return (link_text_len / heading_text_len) > self.hn_config.max_link_density

    def evaluate_demotion(self, heading: Tag) -> tuple[bool, bool]:
        """Evaluates if a heading should be demoted and for what reason."""
        heading_text_len = len(heading.get_text(strip=True))
        demote_by_length = self.should_demote_by_length(heading_text_len)
        demote_by_link_density = self.should_demote_by_link_density(
            heading,
            heading_text_len,
        )
        return demote_by_length, demote_by_link_density


class _HeadingNormalizerConfig:
    """A dedicated configuration object for HeadingNormalizer."""

    MAX_SANE_HEADING_LENGTH: int = 1000

    def __init__(self, config: Any):
        """Initializes and validates all configuration-related attributes."""
        self.config = config
        self.initial_heading_level: int = 1
        self.max_heading_length: int = 150
        self.max_link_density: float = 0.5
        self.bold_paragraph_target_level: int = 2
        self.bold_promotion_requires_solitary_bold_tag: bool = True
        self.bold_promotion_requires_text_only_children: bool = True
        self._validated_heading_classes: dict[str, list[str]] = {}
        self.class_to_level_map: dict[str, str] = {}
        self._validation_messages: list[str] = []

        self._initialize_configuration()
        self._log_validation_summary()

    def _add_warning(self, message: str) -> None:
        """Adds a warning message to the internal list."""
        self._validation_messages.append(message)

    def _log_validation_summary(self) -> None:
        """Logs all collected validation warnings at once."""
        if self._validation_messages:
            log.warning(
                "HeadingNormalizer configuration issues detected (%d issues):\n%s",
                len(self._validation_messages),
                "\n".join(f"- {msg}" for msg in self._validation_messages),
            )

    def _validate_bounded_int(
        self,
        cfg_value: Any,
        cfg_name: str,
        min_val: int,
        max_val: int,
        default: int,
    ) -> int:
        """Validates and clamps an integer configuration value."""
        try:
            value = int(cfg_value)
            if not min_val <= value <= max_val:
                clamped_value = max(min_val, min(value, max_val))
                self._add_warning(
                    f"Configured '{cfg_name}' {value} is outside sane bounds ({min_val}-{max_val}). Clamping to {clamped_value}.",
                )
                return clamped_value
            return value
        except (TypeError, ValueError):
            self._add_warning(
                f"Invalid '{cfg_name}' config value: '{cfg_value}'. Defaulting to {default}.",
            )
            return default

    def _validate_bounded_float(
        self,
        cfg_value: Any,
        cfg_name: str,
        min_val: float,
        max_val: float,
        default: float,
    ) -> float:
        """Validates and clamps a float configuration value."""
        try:
            value = float(cfg_value)
            if not min_val <= value <= max_val:
                clamped_value = max(min_val, min(value, max_val))
                self._add_warning(
                    f"Configured '{cfg_name}' {value} is outside sane bounds ({min_val:.1f}-{max_val:.1f}). Clamping to {clamped_value}.",
                )
                return clamped_value
            return value
        except (TypeError, ValueError):
            self._add_warning(
                f"Invalid '{cfg_name}' config value: '{cfg_value}'. Defaulting to {default:.2f}.",
            )
            return default

    def _initialize_initial_heading_level(self) -> None:
        """Validates and sets the initial heading level from configuration."""
        initial_level_cfg = getattr(self.config, "initial_heading_level", 1)
        self.initial_heading_level = self._validate_bounded_int(
            initial_level_cfg,
            "initial_heading_level",
            MIN_HEADING_LEVEL,
            MAX_HEADING_LEVEL,
            1,
        )

    def _initialize_demotion_thresholds(self) -> None:
        """Validates and sets heading demotion thresholds from configuration."""
        max_heading_length_cfg = getattr(self.config, "max_heading_length", 150)
        max_link_density_cfg = getattr(self.config, "max_link_density", 0.50)

        self.max_heading_length = self._validate_bounded_int(
            max_heading_length_cfg,
            "max_heading_length",
            1,
            self.MAX_SANE_HEADING_LENGTH,
            150,
        )

        self.max_link_density = self._validate_bounded_float(
            max_link_density_cfg,
            "max_link_density",
            0.0,
            1.0,
            0.50,
        )

    def _initialize_bold_promotion_level(self) -> None:
        """Validates and sets the target heading level for bold paragraph promotion."""
        bold_level_str = getattr(
            self.config,
            "bold_paragraph_heading_level",
            "h2",
        )

        bold_level_normalized = str(bold_level_str).lower()
        if level_match := re.match(r"^h(\d+)$", bold_level_normalized):
            raw_level = int(level_match[1])
            clamped_level = max(
                MIN_HEADING_LEVEL,
                min(MAX_HEADING_LEVEL, raw_level),
            )

            if raw_level != clamped_level:
                self._add_warning(
                    f"bold_paragraph_heading_level '{bold_level_str}' out of range. "
                    f"Clamping to 'h{clamped_level}'.",
                )

            self.bold_paragraph_target_level = clamped_level
        else:
            self._add_warning(
                f"Invalid bold_paragraph_heading_level '{bold_level_str}' in config. Defaulting to 'h2'.",
            )
            self.bold_paragraph_target_level = 2

    def _initialize_bold_promotion_heuristics(self) -> None:
        """Loads configuration for bold promotion heuristics."""
        self.bold_promotion_requires_solitary_bold_tag = bool(
            getattr(self.config, "bold_promotion_requires_solitary_bold_tag", True),
        )
        self.bold_promotion_requires_text_only_children = bool(
            getattr(self.config, "bold_promotion_requires_text_only_children", True),
        )

    def _is_valid_heading_level_str(self, level_str: Any) -> bool:
        """Checks if a string is a valid heading level (e.g., 'h1' through 'h6')."""
        return bool(
            isinstance(level_str, str) and HEADING_TAG_RX.match(level_str),
        )

    def _is_valid_heading_classes_list(self, classes: Any) -> bool:
        """Checks if a value is a list of strings."""
        return isinstance(classes, list) and all(isinstance(c, str) for c in classes)

    def _is_valid_css_class_name(self, class_name: str) -> bool:
        """Checks if a string is a valid CSS class name that doesn't require escaping."""
        return bool(_VALID_CSS_CLASS_RX.match(class_name))

    def _process_heading_class_entries(
        self,
        heading_classes_from_context: dict[str, Any],
    ) -> None:
        """Processes entries from config, populates valid ones, and logs errors."""
        invalid_levels: list[str] = []
        invalid_values: dict[str, Any] = {}

        for level_str, classes in heading_classes_from_context.items():
            if not self._is_valid_heading_level_str(level_str):
                invalid_levels.append(str(level_str))
                continue

            if not self._is_valid_heading_classes_list(classes):
                invalid_values[level_str] = classes
                continue

            # Filter out invalid CSS class names to prevent malformed selectors.
            valid_classes = [c for c in classes if self._is_valid_css_class_name(c)]
            if invalid_classes := [
                c for c in classes if not self._is_valid_css_class_name(c)
            ]:
                self._add_warning(
                    f"Invalid CSS class name(s) {sorted(invalid_classes)} found in 'heading_classes' config for level '{level_str}'. "
                    "These classes will be ignored.",
                )

            if valid_classes:
                self._validated_heading_classes[level_str] = valid_classes

        if invalid_levels:
            self._add_warning(
                f"Invalid heading level(s) {', '.join(sorted(invalid_levels))} found in configuration for "
                "class-based promotion. These entries were skipped.",
            )
        if invalid_values:
            self._add_warning(
                f"Invalid value(s) for 'heading_classes' configuration. "
                f"Expected list[str] but got mismatched types for levels: {', '.join(sorted(invalid_values.keys()))}. "
                "These entries were skipped.",
            )

    def _detect_and_log_class_conflicts(self) -> None:
        """Detects and logs ambiguous class mappings for user feedback."""
        class_to_levels = defaultdict(list)
        for level, classes in self._validated_heading_classes.items():
            for class_name in classes:
                class_to_levels[class_name].append(level)

        if conflicts := {
            name: sorted(set(levels))
            for name, levels in class_to_levels.items()
            if len(set(levels)) > 1
        }:
            conflict_messages = [
                f"'{name}' mapped to multiple levels: {lvls}"
                for name, lvls in conflicts.items()
            ]
            self._add_warning(
                "Ambiguous class-based heading configuration detected. The lowest-numbered "
                "(highest-priority) heading level will be used for promotion. "
                f"Conflicts: {'; '.join(conflict_messages)}",
            )

    def _build_final_class_map(self) -> None:
        """Builds the final class-to-level map with an explicit conflict resolution policy.

        This method iterates through the validated heading classes, sorted by heading
        level (e.g., 'h1', 'h2', ...). For each class, it assigns the corresponding
        heading level to the `class_to_level_map`.

        Conflict Resolution Policy: If a class name is mapped to multiple heading
        levels in the configuration (e.g., 'title' is mapped to both 'h1' and 'h2'),
        this method ensures that the lowest-numbered (highest-priority) heading
        level wins. This is achieved by processing levels in ascending order and
        only adding a class to the map if it hasn't been seen before.
        """
        # Sort by numeric heading level (e.g., 1 from 'h1') to ensure a robust
        # priority order, even if non-standard keys were ever to appear.
        sorted_items = sorted(
            self._validated_heading_classes.items(),
            key=lambda item: int(item[0][1:]),
        )
        for level, classes in sorted_items:
            for class_name in classes:
                if class_name not in self.class_to_level_map:
                    self.class_to_level_map[class_name] = level

    def _build_class_to_level_map(self) -> None:
        """
        Detects class conflicts, logs them, and builds the final class-to-level map.

        This method explicitly encodes the conflict resolution strategy: if a class
        is mapped to multiple heading levels, the lowest-numbered (highest-priority)
        level is chosen.
        """
        self._detect_and_log_class_conflicts()
        self._build_final_class_map()

    def _initialize_class_based_promotion_config(self) -> None:
        """Validates and processes the heading_classes configuration from the context."""
        # Pre-validate heading_classes, resolve conflicts, and build a map for
        # efficient promotion.
        heading_classes_from_context = getattr(self.config, "heading_classes", None)

        if heading_classes_from_context is None:
            return

        if not isinstance(heading_classes_from_context, dict):
            self._add_warning(
                "Invalid 'heading_classes' configuration: expected a dict[str, list[str]] "
                f"but got {type(heading_classes_from_context)}. Class-based promotion will be disabled.",
            )
            return

        self._process_heading_class_entries(heading_classes_from_context)
        self._build_class_to_level_map()

    def _initialize_configuration(self) -> None:
        """Initializes and validates all configuration-related attributes."""
        self._initialize_initial_heading_level()
        self._initialize_demotion_thresholds()
        self._initialize_bold_promotion_level()
        self._initialize_class_based_promotion_config()
        self._initialize_bold_promotion_heuristics()


class _ClassPromotionHandler:
    """Handles the logic for promoting elements to headings based on CSS classes."""

    def __init__(
        self,
        context: BookStyleContext,
        class_to_level_map: dict[str, str],
    ):
        self.context = context
        self.class_to_level_map = class_to_level_map

    def _is_heading(self, tag: PageElement) -> bool:
        """Checks if a PageElement is a semantic heading tag (h1-h6)."""
        return isinstance(tag, Tag) and tag.name in VALID_HEADING_TAGS

    def _find_best_promotion_for_tag(
        self,
        tag: Tag,
    ) -> tuple[str, list[str]] | None:
        """Determines the best heading level to promote a tag to based on its classes.

        It finds the highest-priority (lowest number) heading level among all
        promotion classes present on the tag.

        Args:
            tag: The DOM element to evaluate.

        Returns:
            A tuple containing the target heading level string (e.g., 'h1') and a
            list of the classes that triggered the promotion, or None if no promotion
            is warranted.
        """
        tag_classes = coerce_class_list(tag.get("class"))
        best_level_num = 7  # Start with a value higher than any heading level
        target_level_str = ""
        for cls in tag_classes:
            if (level_str := self.class_to_level_map.get(cls)) and (
                level_num := int(level_str[1:])
            ) < best_level_num:
                best_level_num = level_num
                target_level_str = level_str
        if target_level_str:
            promotion_classes = [
                c
                for c in tag_classes
                if (_mapped := self.class_to_level_map.get(c)) == target_level_str
            ]
            return target_level_str, promotion_classes
        return None

    def _promote_single_element_by_class(
        self,
        tag: Tag,
        level: str,
        promotion_classes: list[str],
    ) -> bool:
        """Promotes a single element to a heading if it meets promotion criteria."""
        if self.context.is_inside_code_block(tag) or self._is_heading(tag):
            return False

        tag_classes = coerce_class_list(tag.get("class"))
        current_classes = [c for c in tag_classes if c not in promotion_classes]

        tag.name = level
        if current_classes:
            tag["class"] = " ".join(current_classes)
        elif tag.has_attr("class"):
            del tag["class"]
        return True

    def promote(self, soup: BeautifulSoup) -> int:
        """Promotes elements with specific heading classes to heading tags."""
        promotions = 0
        if not self.class_to_level_map:
            return 0

        selector = ", ".join(f".{c}" for c in self.class_to_level_map)
        for tag in tuple(soup.select(selector)):
            if not isinstance(tag, Tag): # pyright: ignore[reportUnnecessaryIsInstance]
                continue

            if promotion_details := self._find_best_promotion_for_tag(tag):
                target_level_str, promotion_classes = promotion_details
                if self._promote_single_element_by_class(
                    tag,
                    target_level_str,
                    promotion_classes,
                ):
                    promotions += 1
        return promotions


class HeadingNormalizer:
    """
    Normalizes heading elements by promoting styled paragraphs, demoting invalid
    headings, and ensuring a logical, continuous hierarchy.
    """

    def __init__(self, context: BookStyleContext):
        """Initializes the heading normalizer.

        Args:
            context: The shared book context.
        """
        self.context = context
        self.hn_config = _HeadingNormalizerConfig(context.config)
        self.demotion_strategy = _DemotionStrategy(self.hn_config)
        self.headings_promoted: int = 0
        self.headings_demoted: int = 0  # Total unique headings demoted
        self.headings_demoted_by_length: int = 0
        self.headings_demoted_by_link_density: int = 0
        self.hierarchy_fixes: int = 0
        self._current_level: int = 0
        self._reset_state()

    def is_in_initial_state(self) -> bool:
        """Checks if the normalizer is in its initial state for a new book.

        This method provides a guard for testing and orchestration to verify
        that the state has been reset (e.g., by calling `process` with
        `is_new_book_or_document=True`) before processing a new book.

        Returns:
            bool: True if the `_current_level` is in its initial, pre-processing
                state, False otherwise.
        """
        return self._current_level == self.hn_config.initial_heading_level - 1

    def _is_heading(self, tag: PageElement) -> bool:
        """Checks if a PageElement is a semantic heading tag (h1-h6)."""
        return isinstance(tag, Tag) and tag.name in VALID_HEADING_TAGS

    def _reset_state(self) -> None:
        """Resets the internal heading level and telemetry for a new book/document."""
        self._current_level = self.hn_config.initial_heading_level - 1
        self.headings_promoted = 0
        self.headings_demoted = 0
        self.headings_demoted_by_length = 0
        self.headings_demoted_by_link_density = 0
        self.hierarchy_fixes = 0

    def process(
        self,
        soup: BeautifulSoup,
        *,
        is_new_book_or_document: bool = False,
    ) -> tuple[BeautifulSoup, Mapping[str, Any]]:
        """
        Executes the heading normalization pipeline.

        Args:
            soup: The BeautifulSoup object representing the document.
            is_new_book_or_document: If True, resets the hierarchy and telemetry
                state before processing. This should be set for the first
                document of a new book to ensure a clean state.

        Returns:
            A tuple containing the mutated soup and a metadata dictionary.
        """
        if is_new_book_or_document:
            self._reset_state()

        self._promote_styled_paragraphs(soup)

        # Create a snapshot of all headings after the promotion pass.
        all_headings = find_all_snapshot(soup, HEADING_TAG_RX)
        headings_snapshot = tuple(h for h in all_headings if isinstance(h, Tag))

        # First pass: Demote headings based on content rules. This modifies the
        # soup in-place, so some elements in `headings_snapshot` may no longer
        # be headings.
        self._demote_invalid_headings(headings_snapshot)

        # Second pass: Fix hierarchy on the elements that are still headings.
        # We filter the original snapshot to get the list of remaining headings,
        # avoiding a second costly DOM traversal and ensuring we don't process
        # demoted tags.
        remaining_headings = tuple(h for h in headings_snapshot if self._is_heading(h))
        self._fix_hierarchy(remaining_headings)

        return soup, self.get_metadata()

    def _promote_styled_paragraphs(self, soup: BeautifulSoup) -> None:
        """
        Orchestrates the promotion of styled paragraphs to semantic heading tags.

        This method calls a series of helpers to handle different promotion
        heuristics: bold paragraphs, class-based headings, and ARIA roles.

        Args:
            soup: The BeautifulSoup object representing the document.
        """
        self._promote_bold_paragraphs(soup)
        if self.hn_config.class_to_level_map:
            class_promoter = _ClassPromotionHandler(
                self.context,
                self.hn_config.class_to_level_map,
            )
            self.headings_promoted += class_promoter.promote(soup)
        self._promote_aria_headings(soup)

    def _is_valid_bold_promotion_candidate(self, emphasis_tag: Tag) -> bool:
        """Checks if a bold/strong tag is a valid candidate for promotion.

        This helper centralizes the validation logic for bold paragraph promotion,
        checking for code block immunity, parent tag, content, and other configured
        heuristics.

        Args:
            emphasis_tag: The <b> or <strong> tag to evaluate.

        Returns:
            True if the tag is a valid candidate for promotion, False otherwise.
        """
        if self.context.is_inside_code_block(emphasis_tag):
            return False

        p_tag = emphasis_tag.parent
        if not p_tag or p_tag.name != "p":
            return False

        # The emphasis tag must contain non-whitespace text to be a valid heading.
        if not emphasis_tag.get_text(strip=True):
            return False

        # Apply configurable heuristics for solitary child and text-only content.
        return self._is_solitary_emphasis_child(
            emphasis_tag,
            p_tag,
        ) and self._has_text_only_children(emphasis_tag)

    def _is_solitary_emphasis_child(self, emphasis_tag: Tag, p_tag: Tag) -> bool:
        """Checks if a <b> or <strong> tag is the only significant child of its parent <p> tag.

        This check is controlled by the `bold_promotion_requires_solitary_bold_tag`
        configuration flag.

        Args:
            emphasis_tag: The bold or strong tag to check.
            p_tag: The parent paragraph tag.

        Returns:
            True if the check passes or is disabled, False otherwise.
        """
        if not self.hn_config.bold_promotion_requires_solitary_bold_tag:
            return True
        children = [c for c in p_tag.children if not is_ignorable_node(c)]
        return len(children) == 1 and children[0] is emphasis_tag

    def _has_text_only_children(self, emphasis_tag: Tag) -> bool:
        """Checks if a <b> or <strong> tag contains only text nodes (no nested tags).

        This check is controlled by the `bold_promotion_requires_text_only_children`
        configuration flag.

        Args:
            emphasis_tag: The bold or strong tag to check.

        Returns:
            True if the check passes or is disabled, False otherwise.
        """
        if not self.hn_config.bold_promotion_requires_text_only_children:
            return True
        return all(isinstance(c, NavigableString) for c in emphasis_tag.children)

    def _promote_bold_paragraphs(self, soup: BeautifulSoup) -> None:
        """Promotes paragraphs styled as headings with bold or strong text.

        This method iterates over all `<b>` and `<strong>` tags for performance
        and checks if they are candidates for promotion to a heading. The promotion
        heuristics are configurable to allow for stricter or looser matching.

        Default Heuristics (configurable):
        - The `<b>` or `<strong>` tag's parent must be a `<p>` tag.
        - The `<b>` or `<strong>` tag must be the only significant child of the
          `<p>` tag.
        - The `<b>` or `<strong>` tag must contain only text nodes (no nested
          links, etc.).

        Paragraphs where the bold text is empty or whitespace-only are always skipped.
        """
        # Iterate over <b> and <strong> tags for performance, as they are less
        # common than <p> tags.
        for emphasis_tag in find_all_snapshot(soup, ["b", "strong"]):
            # The find_all_snapshot with tag names ensures this is a Tag.
            if self._is_valid_bold_promotion_candidate(cast(Tag, emphasis_tag)):
                # The candidate check ensures parent is a <p> tag.
                p_tag = cast(Tag, emphasis_tag.parent)
                p_tag.name = f"h{self.hn_config.bold_paragraph_target_level}"
                emphasis_tag.unwrap()
                self.headings_promoted += 1

    def _cleanup_native_aria_heading(self, tag: Tag) -> None:
        """Removes redundant ARIA heading attributes from a native heading tag.

        Args:
            tag: The native heading tag (h1-h6) to clean up.
        """
        if tag.has_attr("role"):
            del tag["role"]
        if tag.has_attr("aria-level"):
            del tag["aria-level"]

    def _promote_non_native_aria_heading(self, tag: Tag) -> None:
        """Promotes a non-native tag with an ARIA heading role to a semantic heading.

        This method reads the `aria-level`, clamps it to the valid h1-h6 range,
        mutates the tag name, and cleans up the ARIA attributes.

        Args:
            tag: The non-native heading tag to promote.
        """
        aria_level_str = tag.get("aria-level")
        if not (isinstance(aria_level_str, str) and aria_level_str.isdigit()):
            return

        original_level = int(aria_level_str)
        level = original_level
        # Clamp out-of-range levels into our supported range
        if not MIN_HEADING_LEVEL <= level <= MAX_HEADING_LEVEL:
            level = min(
                MAX_HEADING_LEVEL,
                max(MIN_HEADING_LEVEL, level),
            )
            log.debug(
                "Clamped out-of-range aria-level %s to %s for ARIA heading",
                original_level,
                level,
            )

        tag.name = f"h{level}"
        del tag["role"]
        if tag.has_attr("aria-level"):
            del tag["aria-level"]
        self.headings_promoted += 1

    def _promote_aria_headings(self, soup: BeautifulSoup) -> None:
        """Converts elements with ARIA heading roles to semantic heading tags.
        Elements with out-of-range aria-level values are clamped into the
        supported heading range so they still participate in the heading
        hierarchy. This method skips native h1-h6 tags, only cleaning up their
        redundant ARIA attributes.
        """
        for tag in find_all_snapshot(soup, attrs={"role": "heading"}):
            if not isinstance(tag, Tag) or self.context.is_inside_code_block(tag):
                continue

            # If it's already a semantic heading, just clean up redundant ARIA roles.
            if self._is_heading(tag):
                self._cleanup_native_aria_heading(tag)
            else:
                self._promote_non_native_aria_heading(tag)

    def _demote_invalid_headings(self, headings: tuple[Tag, ...]) -> None:
        """Demotes heading tags that violate length or link density rules to paragraphs.

        This method iterates through a snapshot of heading tags and applies demotion
        rules based on their text content length and link density. The actual
        demotion logic for each individual heading is delegated to
        `_demote_single_heading`.

        Args:
            headings: A snapshot of heading elements to evaluate.

        Returns:
            None

        Mutations:
            - Calls `_demote_single_heading` which may modify heading tags in-place.
            - Updates telemetry counters for demoted headings.
        """
        for heading in headings:
            if not self.context.is_inside_code_block(heading):
                self._demote_single_heading(heading)

    def _apply_demotion_mutation(self, heading: Tag) -> None:
        """Mutates a heading tag to a paragraph, preserving the original level."""
        heading["data-demoted-from"] = heading.name
        heading.name = "p"

    def _demote_single_heading(self, heading: Tag) -> bool:
        """Applies demotion rules to a single heading based on length and link density.

        This method delegates the evaluation of demotion criteria to the
        `_DemotionStrategy` object.

        Args:
            heading (Tag): The heading element to evaluate and potentially demote.

        Returns:
            bool: True if the heading was demoted, False otherwise.
        """
        if not heading.get_text(strip=True):
            return False

        demote_by_length, demote_by_link_density = (
            self.demotion_strategy.evaluate_demotion(
                heading,
            )
        )

        was_demoted = False
        if demote_by_length:
            self._apply_demotion_mutation(heading)
            self.headings_demoted_by_length += 1
            was_demoted = True
        elif demote_by_link_density:
            self._apply_demotion_mutation(heading)
            self.headings_demoted_by_link_density += 1
            was_demoted = True

        if was_demoted:
            self.headings_demoted += 1
        return was_demoted

    def _handle_initial_heading(self, level: int) -> bool:
        """Handles the first heading in a sequence, setting the baseline level.

        Args:
            level: The integer level of the heading.

        Returns:
            True if it was the initial heading, False otherwise.
        """
        if self.is_in_initial_state():
            self._current_level = level
            return True
        return False

    def _fix_hierarchy(self, headings: tuple[Tag, ...]) -> None:
        """Ensures the heading hierarchy is continuous and logical.

        Args:
            headings: A snapshot of heading elements to process,
                which should have been pre-filtered to exclude any demoted headings.
        """
        for heading in headings:
            if self.context.is_inside_code_block(heading):
                continue

            level = int(heading.name[1:])

            if self._handle_initial_heading(level):
                continue

            # Per the specification, when an invalid upward jump is detected (e.g., h1
            # followed by h4), the heading is corrected to the next logical level
            # (h2 in this case), rather than snapping to a different level. This
            # ensures a strictly continuous hierarchy is enforced, as per
            # `specs/normalizers/heading_normalizer.md`
            if level > self._current_level + 1:
                new_level = self._current_level + 1
                heading.name = f"h{new_level}"
                self._current_level = new_level
                self.hierarchy_fixes += 1
            else:
                # Any downward jump (e.g., h4 -> h2) or same-level entry is
                # considered a valid "structural re-entry" as per the spec.
                # The hierarchy simply continues from this new, lower level.
                self._current_level = level

    def get_metadata(self) -> Mapping[str, Any]:
        """Constructs the metadata dictionary for the processing results.

        This method computes the final pipeline status based on whether any
        changes were made and then generates the standard metadata payload.

        Returns:
            A dictionary conforming to the canonical metadata contract.
        """
        has_changes = (
            self.headings_promoted > 0
            or self.headings_demoted > 0
            or self.hierarchy_fixes > 0
        )
        status = PipelineStatus.SUCCESS if has_changes else PipelineStatus.SUCCESS_NOOP
        return generate_processor_metadata(
            processor_key="heading_normalization",
            status=status,
            headings_promoted=self.headings_promoted,
            headings_demoted=self.headings_demoted,  # Total unique demotions
            headings_demoted_by_length=self.headings_demoted_by_length,
            headings_demoted_by_link_density=self.headings_demoted_by_link_density,
            hierarchy_fixes=self.hierarchy_fixes,
        )
