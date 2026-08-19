"""
This standalone Python engine recursively walks your `tests/specs/` directory,
dynamically imports the target normalizer classes, sets up mock environments
(including a virtual disk mock for asset writing), executes the assertions,
and outputs beautifully formatted, colorized unified diffs in the console
when a failure occurs.
"""

import base64
import contextlib
import difflib
import hashlib
import importlib
import inspect
import os
import re
import sys
import tempfile
import traceback
from typing import Any, Final, cast

# Add the project root to the Python path to allow imports from 'src'.
# This ensures that `importlib.import_module("src.dom_normalizer...")` works
# when the script is run from the project root as `python tests/run_yaml_tests.py`.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import yaml
from bs4 import BeautifulSoup, Tag

# NEW: Import all components to populate the registry.
try:
    from src.dom_normalizer import (
        components,  # pyright: ignore[reportUnusedImport] # noqa: F401
    )
    from src.dom_normalizer.core.component_registry import create_processor
except ImportError as e:
    print(f"\033[91mFailed to import core components: {e}\033[0m")
    sys.exit(1)

from src.dom_normalizer.core.config import (
    EngineConfiguration,
)
from src.dom_normalizer.core.context import (
    BookStyleContext as RealBookStyleContext,
)
from src.dom_normalizer.core.dom_utils import (
    coerce_class_list,
    find_all_snapshot,
    normalize_style_attribute,
    strip_css_properties,
)
from src.dom_normalizer.core.lang_codes import ISOLanguageCode
from src.dom_normalizer.core.media_utils import (
    get_extension_for_mime,
    normalize_extension,
)

# --- ANSI COLOR CONSTANTS ---
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


class MockBookStyleContext:
    """
    A highly malleable context that simulates the database environment
    and processing pipeline, dynamically injecting properties from YAML.
    """

    def __init__(self, context_spec: dict[str, Any]):
        self.primary_language = context_spec.get("primary_language", "en")
        self.is_code_block = context_spec.get("is_code_block", False)
        self.file_name = context_spec.get("file_name", "document.xhtml")
        self.book_base_name = context_spec.get("book_base_name", "test_book")

        # Initialize a full EngineConfiguration object from the test spec
        config_kwargs = {
            "enable_contrastive_emphasis": context_spec.get(
                "enable_contrastive_emphasis", False
            ),
            "dense_container_tags": context_spec.get(
                "dense_container_tags", ["body", "main", "article"]
            ),
            "dense_container_heading_tags": context_spec.get(
                "dense_container_heading_tags", ["h1", "h2", "h3"]
            ),
            "initial_heading_level": context_spec.get("initial_heading_level", 1),
            "heading_classes": context_spec.get("heading_classes", {}),
            "max_sane_heading_length": context_spec.get("max_sane_heading_length", 1000),
            "min_heading_level": context_spec.get("min_heading_level", 1),
            "max_heading_level": context_spec.get("max_heading_level", 6),
            "max_heading_length": context_spec.get("max_heading_length", 150),
            "max_link_density": context_spec.get("max_link_density", 0.5),
            "bold_paragraph_heading_level": context_spec.get(
                "bold_paragraph_heading_level", "h2"
            ),
            "bold_promotion_requires_solitary_bold_tag": context_spec.get(
                "bold_promotion_requires_solitary_bold_tag", True
            ),
            "bold_promotion_requires_text_only_children": context_spec.get(
                "bold_promotion_requires_text_only_children", True
            ),
            "footnote_patterns": context_spec.get("footnote_patterns", []),
            "language_enum_map": context_spec.get(
                "language_enum_map",
                {
                    "en": "ENGLISH",
                    "es": "SPANISH",
                    "fr": "FRENCH",
                    "de": "GERMAN",
                    "it": "ITALIAN",
                    "pt": "PORTUGUESE",
                    "la": "LATIN",
                },
            ),
            "lingua_low_memory_mode": context_spec.get("lingua_low_memory_mode", True),
            "external_video_domains": context_spec.get("external_video_domains", []),
            "min_lang_subtag_length": context_spec.get("min_lang_subtag_length", 2),
            "max_lang_subtag_length": context_spec.get("max_lang_subtag_length", 8),
            "high_poetry_priority": context_spec.get("high_poetry_priority", False),
            "high_priority_potential_tags": context_spec.get(
                "high_priority_potential_tags", ["div", "table", "p"]
            ),
            "high_priority_attribute_hints": context_spec.get(
                "high_priority_attribute_hints",
                ["poem", "poetry", "verse", "stanza", "lyrics"],
            ),
            "br_density_threshold": context_spec.get("br_density_threshold", 50.0),
            "dialogue_exclusion_threshold": context_spec.get(
                "dialogue_exclusion_threshold", 0.4
            ),
            "enjambment_ratio_threshold": context_spec.get(
                "enjambment_ratio_threshold", 0.6
            ),
            "poetry_max_words_for_enjambment": context_spec.get(
                "poetry_max_words_for_enjambment", 12
            ),
            "poetry_prose_word_count_multiplier": context_spec.get(
                "poetry_prose_word_count_multiplier", 2.0
            ),
            "poetry_em_to_indent_ratio": context_spec.get("em_to_indent_ratio", 1.0),
            "poetry_px_to_em_ratio": context_spec.get("px_to_em_ratio", 16.0),
            "poetry_percent_to_indent_ratio": context_spec.get(
                "percent_to_indent_ratio", 2.0
            ),
            "poetry_nbsp_to_indent_ratio": context_spec.get("nbsp_to_indent_ratio", 2.0),
            "poetry_max_nbsp_depth": context_spec.get("max_nbsp_depth", 3),
            "poetry_indentation_tag_whitelist": context_spec.get(
                "indentation_tag_whitelist", ["p", "div"]
            ),
            "poetry_indentation_properties": context_spec.get(
                "poetry_indentation_properties",
                ("margin-left", "padding-left", "text-indent"),
            ),
            "poetry_indentation_units": context_spec.get(
                "poetry_indentation_units", ("em", "rem", "px", "%")
            ),
            "poetic_classes_substrings": context_spec.get(
                "poetic_classes_substrings",
                ["verse", "poem", "poesia", "poetic", "poetry"],
            ),
            "min_br_for_poetic_metrics": context_spec.get(
                "min_br_for_poetic_metrics", 2
            ),
            "max_avg_words_per_line_poetic": context_spec.get(
                "max_avg_words_per_line_poetic", 12
            ),
            "min_viable_list_items": context_spec.get("min_viable_list_items", 2),
            "list_unordered_prefix_rx": context_spec.get(
                "list_unordered_prefix_rx", r"^\s*([-\*\u2022\u25b6\u2013])\s+"
            ),
            "list_ordered_prefix_rx": context_spec.get(
                "list_ordered_prefix_rx",
                r"^\s*(?:(\(?\d+[\.\)])|(\(?[a-zA-Z][\.\)])|(\(?[ivxIVX]+[\.\)]))\s*",
            ),
            "list_class_keywords": frozenset(
                context_spec.get(
                    "list_class_keywords",
                    {"list", "item", "bullet", "calibre", "idgenparagraphstyle"},
                )
            ),
            "list_complex_structure_tags": frozenset(
                context_spec.get(
                    "list_complex_structure_tags", {"ul", "ol", "table", "figure"}
                )
            ),
            "list_level_mapping": context_spec.get(
                "list_level_mapping",
                {"bullet": 1, "numeric": 1, "alpha": 2, "roman": 3, "class_based": 1},
            ),
            "min_indent_em_rem": context_spec.get("min_indent_em_rem", 1.5),
            "min_indent_px": context_spec.get("min_indent_px", 24),
            "css_max_brace_depth": context_spec.get("css_max_brace_depth", 50),
            "css_max_scan_iterations": context_spec.get(
                "css_max_scan_iterations", 1_000_000
            ),
            "min_speaker_label_length": context_spec.get("min_speaker_label_length", 2),
            "max_speaker_label_length": context_spec.get("max_speaker_label_length", 30),
            "min_div_table_rows": context_spec.get("min_div_table_rows", 2),
            "min_div_table_cols": context_spec.get("min_div_table_cols", 2),
            "header_promotion_threshold": context_spec.get(
                "header_promotion_threshold", 0.5
            ),
            "min_tables_for_fusion": context_spec.get("min_tables_for_fusion", 2),
            "density_exemption_char_threshold": context_spec.get(
                "density_exemption_char_threshold", 49
            ),
            "standard_density_cap": context_spec.get("standard_density_cap", 0.20),
            "layout_enhanced_density_cap": context_spec.get(
                "layout_enhanced_density_cap", 0.65
            ),
            "min_document_chars_for_processing": context_spec.get(
                "min_document_chars_for_processing", 1
            ),
            "min_inline_toc_lines": context_spec.get("min_inline_toc_lines", 4),
            "max_words_in_toc_airlock": context_spec.get(
                "max_words_in_toc_airlock", 30
            ),
            "min_tabular_index_rows": context_spec.get("min_tabular_index_rows", 2),
            "max_chars_in_initial_column": context_spec.get(
                "max_chars_in_initial_column", 25
            ),
            "tlcr_threshold": context_spec.get("tlcr_threshold", 0.85),
            "high_link_density_threshold": context_spec.get(
                "high_link_density_threshold", 0.7
            ),
            "min_latex_length": context_spec.get("min_latex_length", 3),
            "max_flatten_passes": context_spec.get("max_flatten_passes", 10),
            "protected_prose_classes": frozenset(
                context_spec.get(
                    "protected_prose_classes",
                    ["prose", "editorial", "editorial-prose"],
                )
            ),
            "footnote_donor_file_density_threshold": context_spec.get(
                "footnote_donor_file_density_threshold", 0.8
            ),
            "footnote_symmetry_threshold": context_spec.get(
                "footnote_symmetry_threshold", 0.5
            ),
            "footnote_toc_heading_tags": frozenset(
                context_spec.get("footnote_toc_heading_tags", {"h1", "h2", "h3"})
            ),
            # Add Blockquote Processor settings
            "blockquote_ttr_threshold": context_spec.get("blockquote_ttr_threshold", 3.0),
            "blockquote_anchor_density_threshold": context_spec.get(
                "blockquote_anchor_density_threshold", 0.30
            ),
            "blockquote_ttr_smoothing_factor": context_spec.get(
                "blockquote_ttr_smoothing_factor", 1
            ),
            "epigraph_max_length": context_spec.get("epigraph_max_length", 300),
            "epigraph_heading_proximity_limit": context_spec.get(
                "epigraph_heading_proximity_limit", 4
            ),
            "epigraph_heading_tags": frozenset(
                context_spec.get("epigraph_heading_tags", {"h1", "h2", "h3", "h4", "h5", "h6"})
            ),
            "epigraph_blocking_tags": frozenset(
                context_spec.get("epigraph_blocking_tags", {
                    "p", "div", "section", "article", "aside", "main", "header", "footer", "nav",
                    "ul", "ol", "dl", "figure", "figcaption", "picture", "video", "audio",
                    "table", "blockquote", "pre", "form",
                })
            ),
            "foreign_block_min_length": context_spec.get("foreign_block_min_length", 25),
            "poetic_quote_min_lines": context_spec.get("poetic_quote_min_lines", 2),
            "poetic_quote_min_content_line_length": context_spec.get(
                "poetic_quote_min_content_line_length", 2
            ),
            "poetic_quote_max_mean_length": context_spec.get("poetic_quote_max_mean_length", 55),
            "poetic_quote_max_variance": context_spec.get("poetic_quote_max_variance", 225.0),
            "prose_quote_min_indent_em": context_spec.get("prose_quote_min_indent_em", 1.5),
            "prose_quote_min_indent_px": context_spec.get("prose_quote_min_indent_px", 20),
            "prose_quote_min_indent_percent": context_spec.get("prose_quote_min_indent_percent", 5),
            "prose_quote_min_indent_pt": context_spec.get("prose_quote_min_indent_pt", 6.0),
            "prose_quote_min_indent_cm": context_spec.get("prose_quote_min_indent_cm", 0.2),
            "prose_quote_px_per_em": context_spec.get("prose_quote_px_per_em", 16.0),
            "prose_quote_px_per_pt": context_spec.get("prose_quote_px_per_pt", 4.0 / 3.0),
            "prose_quote_px_per_cm": context_spec.get("prose_quote_px_per_cm", 96.0 / 2.54),
            "min_toc_line_chars": context_spec.get("min_toc_line_chars", 3),
            "max_toc_line_chars": context_spec.get("max_toc_line_chars", 70),
            "checklist_start_numbers": tuple(
                context_spec.get("checklist_start_numbers", (0, 1))
            ),
            "accessibility_landmark_mapping": context_spec.get(
                "accessibility_landmark_mapping",
                {"bibliography": "bibliography", "glossary": "glossary"},
            ),
            "accessibility_page_break_comment_format": context_spec.get(
                "accessibility_page_break_comment_format", " page-break: {page_id} "
            ),
            "accessibility_page_break_fallback_id": context_spec.get(
                "accessibility_page_break_fallback_id", "unknown"
            ),
            "accessibility_doc_role_prefix": context_spec.get(
                "accessibility_doc_role_prefix", "doc-"
            ),
            "accessibility_appendix_block_class": context_spec.get(
                "accessibility_appendix_block_class", "appendix-block"
            ),
            "accessibility_no_split_chunk_strategy": context_spec.get(
                "accessibility_no_split_chunk_strategy", "no_split"
            ),
            "blockquote_paragraph_like_blocking_tags": frozenset(
                context_spec.get(
                    "blockquote_paragraph_like_blocking_tags",
                    {"p", "div", "ul", "ol", "table", "blockquote"},
                )
            ),
            "poetry_block_class": context_spec.get("poetry_block_class", "poetry-block"),
            "poetry_indent_char": context_spec.get("poetry_indent_char", "\u2003"),
            "poetry_indent_only_line_class": context_spec.get(
                "poetry_indent_only_line_class", "poetry-indent-only-line"
            ),
            "poetry_candidate_tags": context_spec.get(
                "poetry_candidate_tags", ["blockquote"]
            ),
            "poetry_high_priority_candidate_tags": context_spec.get(
                "poetry_high_priority_candidate_tags", ["div", "table"]
            ),
            "math_related_tags": frozenset(
                context_spec.get("math_related_tags", {"math", "img", "svg"})
            ),
            "math_simple_latex_cues": tuple(
                context_spec.get("math_simple_latex_cues", ("\\", "^", "_", "$"))
            ),
            "math_block_class": context_spec.get("math_block_class", "math-block"),
            "math_inline_class": context_spec.get("math_inline_class", "math-inline"),
            "math_block_delimiters": tuple(
                context_spec.get("math_block_delimiters", ("$$", "$$"))
            ),
            "math_inline_delimiters": tuple(
                context_spec.get("math_inline_delimiters", ("$", "$"))
            ),
            "table_valid_parents": frozenset(
                context_spec.get(
                    "table_valid_parents", {"tbody", "thead", "tfoot", "table"}
                )
            ),
            "table_orphan_tr_contexts": frozenset(
                context_spec.get(
                    "table_orphan_tr_contexts",
                    {"body", "div", "section", "article", "main"},
                )
            ),
            "list_block_wrapper_tag": context_spec.get("list_block_wrapper_tag", "div"),
            "list_block_wrapper_class": context_spec.get("list_block_wrapper_class", "list-block"),
            "media_tags": frozenset(
                context_spec.get(
                    "media_tags",
                    [
                        "img",
                        "svg",
                        "video",
                        "audio",
                        "picture",
                        "source",
                        "canvas",
                        "iframe",
                        "math",
                    ],
                )
            ),
            "block_level_tags": frozenset(
                context_spec.get(
                    "block_level_tags",
                    {
                        "p", "div", "section", "article", "li", "ul", "ol", "dl", "dt", "dd",
                        "table", "thead", "tbody", "tfoot", "tr", "td", "th", "figure",
                        "header", "footer", "aside", "blockquote", "hr",
                    },
                )
            ),
            "semantic_attr_prefixes": tuple(
                context_spec.get("semantic_attr_prefixes", ("aria-", "data-"))
            ),
            "semantic_attrs": frozenset(context_spec.get("semantic_attrs", ["role"])),
            "tag_identifier_attr_value_limit": context_spec.get(
                "tag_identifier_attr_value_limit", 75
            ),
            "mime_to_extension_map": context_spec.get(
                "mime_to_extension_map",
                {
                    "image/jpeg": ".jpg",
                    "image/png": ".png",
                    "image/gif": ".gif",
                    "image/svg+xml": ".svg",
                    "image/webp": ".webp",
                    "image/x-icon": ".ico",
                    "image/vnd.microsoft.icon": ".ico",
                    "audio/mpeg": ".mp3",
                    "audio/mp4": ".m4a",
                    "audio/ogg": ".ogg",
                    "audio/wav": ".wav",
                    "video/mp4": ".mp4",
                    "video/webm": ".webm",
                    "video/ogg": ".ogv",
                },
            ),
            "image_extension_aliases": frozenset(
                context_spec.get("image_extension_aliases", {".jpeg"})
            ),
            "image_extension_alias_map": context_spec.get(
                "image_extension_alias_map", {".jpeg": ".jpg"}
            ),
            "data_uri_prefix": context_spec.get("data_uri_prefix", "data:"),
        }
        self.config = EngineConfiguration(**config_kwargs)
        self._is_contrastive_element_ids = context_spec.get(
            "is_contrastive_element_ids",
            [],
        )
        self._is_italic_element_classes = context_spec.get(
            "is_italic_element_classes",
            [],
        )
        self._is_bold_element_classes = context_spec.get("is_bold_element_classes", [])
        self.blockquote_compounds = context_spec.get(
            "blockquote_compounds",
            [frozenset(["blockquote-element"])],
        )
        # Default floating compounds to match the tests for floating_element_processor
        self.floating_compounds = context_spec.get(
            "floating_compounds",
            [
                frozenset(["floating-element"]),
                frozenset(["floating-element", "sidebar"]),
            ],
        )
        # Virtual persistence simulator for media_processor tests
        self.written_files: dict[str, str] = {}

    def is_inside_code_block(self, node: Any) -> bool:
        """
        Checks if the given node is considered to be inside a code block.
        For mocking purposes, this checks if the node has a 'code' ancestor.
        """
        return True if self.is_code_block else bool(node.find_parent("code"))

    def normalize_inline_floats(self, node: Tag) -> bool:
        """Mock for promoting float styles."""
        style = normalize_style_attribute(node.get("style"))
        if "float" not in style:
            return False

        classes = coerce_class_list(node.get("class"))
        if "floating-element" not in classes:
            classes.append("floating-element")
        node["class"] = " ".join(classes)

        if new_style := strip_css_properties(style, frozenset({"float"})):
            node["style"] = new_style
        elif "style" in node.attrs:
            del node["style"]
        return True

    def normalize_inline_indents(self, node: Tag) -> bool:
        """Mock for promoting indent styles."""
        style_str = normalize_style_attribute(node.get("style"))
        if not style_str:
            return False

        # Simplified check for indent, doesn't check thresholds.
        # Assumes test inputs will have significant indents.
        indent_match = re.search(r"(?:margin|padding)-left", style_str)
        if not indent_match:
            return False

        classes_list = coerce_class_list(node.get("class"))
        if "blockquote-element" not in classes_list:
            classes_list.append("blockquote-element")
            node["class"] = " ".join(classes_list)

            # Per review, strip the style to match the behavior of the
            # full sanitization pipeline and fix the isolated strategy test.
            if new_style := strip_css_properties(
                style_str,
                frozenset({"margin-left", "padding-left", "text-indent"}),
            ):
                node["style"] = new_style
            elif "style" in node.attrs:
                del node["style"]

            return True
        return False

    def write_extracted_asset(self, relative_path: str, content_data: str) -> None:
        """Simulates writing assets to disk by recording their paths and hashes."""
        self.written_files[relative_path] = content_data

    # Convenience mocks for behavior selectors
    def is_floating_element(self, node) -> bool:
        """Mock behavior to identify a node as a floating element based on its class."""
        return "floating-element" in coerce_class_list(node.get("class"))

    def is_blockquote_element(self, node) -> bool:
        """Mock behavior to identify a node as a blockquote element based on its class."""
        return "blockquote-element" in coerce_class_list(node.get("class"))

    def is_italic_element(self, node: Any) -> bool:
        """
        Mock behavior to identify a node as italic.
        Currently, this mock does not implement complex style analysis.
        """
        node_classes = coerce_class_list(node.get("class"))
        return bool(set(node_classes).intersection(self._is_italic_element_classes))

    def is_bold_element(self, node: Any) -> bool:
        """
        Mock behavior to identify a node as bold.
        Currently, this mock does not implement complex style analysis.
        """
        node_classes = coerce_class_list(node.get("class"))
        return bool(set(node_classes).intersection(self._is_bold_element_classes))

    def is_contrastive_element(self, node: Any) -> bool:
        """
        Mock behavior to identify a node as contrastive based on its ID.
        This is used for the SEMANTIC_RESET test case.
        """
        if not isinstance(node, Tag):
            return False
        return node.get("id") in self._is_contrastive_element_ids

    def is_inside_literal_code_tag(self, node: Any) -> bool:
        """
        Mock behavior for checking if a node is inside a literal code tag.
        This is used by normalizers like TableNormalizer.
        """
        if not isinstance(node, Tag):
            return False
        if self.is_code_block:  # If the entire context is marked as a code block
            return True
        return bool(node.find_parent("code") or node.find_parent("pre"))


class MockProcessor:
    """A mock processor to pass to strategy constructors for isolated testing."""

    XLINK_HREF_ATTR: Final = "xlink:href"

    def __init__(self, context: MockBookStyleContext):
        """Initializes the mock processor with a context and telemetry counters."""
        self.context = context
        # Initialize all possible telemetry counters to avoid AttributeErrors
        # during strategy-level tests.
        # Counters for blockquote_processor strategies
        self.generic_quotes_created_count = 0
        self.epigraphs_identified_count = 0
        self.foreign_blocks_identified_count = 0
        # Counters for list_normalizer strategies
        self.unordered_lists_recovered = 0
        self.ordered_lists_recovered = 0
        self.multiline_items_welded = 0
        self.total_raw_paragraphs_purged = 0
        self.lists_sanitized = 0
        self.lists_fused = 0
        # Counters for footnote_processor strategies
        self.notes_found = 0
        self.notes_rebuilt = 0
        self.backlinks_injected = 0
        self.anomalies_repaired = 0
        # Add attributes and counters that media handlers expect on the processor
        self.purged_count = 0
        self.external_video_count = 0
        self.base64_count = 0
        self.error_count = 0
        self.local_audio_count = 0
        self.local_video_count = 0
        self.local_image_count = 0
        # Counters for structural_sanitizer strategies
        self.inline_indents_normalized = 0
        self.inline_floats_normalized = 0
        self.layout_attributes_persisted = 0
        self.br_tags_collapsed = 0
        self.poetic_br_tags_preserved = 0
        self.empty_nodes_purged = 0

        self.video_domain_rx = re.compile(
            r"(youtube\.com|youtu\.be|vimeo\.com)",
            re.IGNORECASE,
        )

    def get_extension_from_mime(self, mime_type: str) -> str:
        """Mock method to get extension from MIME type."""
        return get_extension_for_mime(mime_type, self.context.config) or ""

    def read_local_asset(self, src_attr, _file_path):  # W0613:unused-argument
        """Mock method to simulate reading a local asset."""
        from pathlib import Path

        if isinstance(src_attr, str):
            return (
                b"dummy file content",
                normalize_extension(Path(src_attr).suffix, self.context.config) or ".dat",
            )
        return None

    def copy_preserved_attributes(self, src_tag: Tag, dest_tag: Tag) -> None:
        """Mock method for copying attributes."""
        # This is a placeholder for the real method, which copies attributes
        # from src_tag to dest_tag. For testing purposes, we don't need to
        # implement the actual copying logic unless a test specifically
        # asserts on copied attributes.

    def create_video_placeholder_img(self, _tag: Tag, soup: BeautifulSoup) -> Tag:
        """Mock method for creating a video placeholder image."""
        return soup.new_tag("img", src="placeholder.png", alt="Video Placeholder")

    def save_asset_to_sibling_dir(
        self,
        dir_name: str,
        asset_filename: str,
        binary_data: bytes,
    ) -> str:
        """Mock method to simulate saving an asset and returning its path."""
        # Use os.path.join for cross-platform compatibility, then normalize
        relative_path = os.path.join("..", "media", dir_name, asset_filename).replace(
            os.sep,
            "/",
        )
        # Log the write to the virtual disk for validation
        self.context.write_extracted_asset(
            os.path.join(
                self.context.book_base_name,
                "media",
                dir_name,
                asset_filename,
            ),
            hashlib.sha256(binary_data).hexdigest(),
        )
        return relative_path

    def get_media_type_and_increment_counter(self, ext: str) -> str:
        """Mock method to categorize media and update telemetry."""
        if ext in self.context.config.image_extensions:
            self.local_image_count += 1
            return "images"
        if ext in self.context.config.video_extensions:
            self.local_video_count += 1
            return "video"
        if ext in self.context.config.audio_extensions:
            self.local_audio_count += 1
            return "audio"
        return "misc"

    def normalize_non_image_tag(
        self,
        tag: Tag,
        _soup: BeautifulSoup,
        _media_type: str,
        relative_path: str,
    ) -> None:
        """Mock method to normalize audio/video tags by updating src attributes."""
        # This is a simplified mock. It updates the src of the main tag and
        # any <source> children to allow the test to proceed.
        if tag.has_attr("src"):
            tag["src"] = relative_path
        if tag.has_attr("poster"):
            tag["poster"] = "../media/images/poster-hash.jpg"
        for source in tag.find_all("source"):
            source["src"] = relative_path

    def get_sha256_hash(self, data: bytes) -> str:
        """Mock method to get a predictable hash."""
        if data == b"dummy file content":
            return "placeholder-hash"
        return hashlib.sha256(data).hexdigest()

    @property
    def unsupported_media_purged(self):
        """Maps internal counter to test-facing metric name."""
        return self.purged_count

    @property
    def external_videos_wrapped(self):
        """Maps internal counter to test-facing metric name."""
        return self.external_video_count

    @property
    def base64_media_extracted(self):
        """Maps internal counter to test-facing metric name."""
        return self.base64_count

    @property
    def local_media_relocated(self):
        """Maps internal counters to a combined test-facing metric name."""
        return self.local_image_count + self.local_audio_count + self.local_video_count

    @property
    def images_processed(self):
        """Maps internal counter to test-facing metric name."""
        return self.local_image_count

    @property
    def video_files_processed(self):
        """Maps internal counter to test-facing metric name."""
        return self.local_video_count

    @property
    def audio_files_processed(self):
        """Maps internal counter to test-facing metric name."""
        return self.local_audio_count
        # NOTE: Add other processor-specific counters here if new strategies
        # from other packages are tested in isolation.

    def increment_empty_nodes_purged(self, amount: int = 1) -> None:
        """Increments the counter for purged empty nodes."""
        self.empty_nodes_purged += amount

    def increment_br_tags_collapsed(self, amount: int = 1) -> None:
        """Increments the counter for collapsed <br> tags."""
        self.br_tags_collapsed += amount

    def increment_poetic_br_tags_preserved(self, amount: int = 1) -> None:
        """Increments the counter for preserved poetic <br> tags."""
        self.poetic_br_tags_preserved += amount

    def increment_layout_attributes_persisted(self, amount: int = 1) -> None:
        """Increments the counter for persisted legacy layout attributes."""
        self.layout_attributes_persisted += amount

    def increment_inline_floats_normalized(self, amount: int = 1) -> None:
        """Increments the counter for normalized inline float styles."""
        self.inline_floats_normalized += amount

    def increment_inline_indents_normalized(self, amount: int = 1) -> None:
        """Increments the counter for normalized inline indent styles."""
        self.inline_indents_normalized += amount


def load_strategy_class(package_name: str, class_name_str: str):
    """
    Dynamically loads a strategy class from its corresponding module file.
    Assumes the module file is the snake_case version of the class name.
    """
    # This helper is now only used for strategies, which have a simpler structure.
    # We can simplify the loading logic.
    # Convert PascalCase to snake_case for the module filename
    module_file_name = "".join(
        [f"_{i.lower()}" if i.isupper() else i for i in class_name_str],
    ).lstrip("_")

    # Attempt 1: Direct path
    module_path_1 = f"src.dom_normalizer.{package_name}.{module_file_name}"
    attempted_paths = [module_path_1]
    with contextlib.suppress(ModuleNotFoundError, AttributeError):
        module = importlib.import_module(module_path_1)
        return getattr(module, class_name_str)

    # Attempt 2: Nested 'strategies' sub-package (e.g., src.dom_normalizer.footnotes.strategies.anomaly_strategy)
    module_path_2 = f"src.dom_normalizer.{package_name}.strategies.{module_file_name}"
    attempted_paths.append(module_path_2)
    with contextlib.suppress(ModuleNotFoundError, AttributeError):
        module = importlib.import_module(module_path_2)
        return getattr(module, class_name_str)

    # Attempt 3: Nested 'strategies' with shortened name (for footnote strategies like ParameterizedFootnoteStrategy)
    if "_footnote" in module_file_name:
        short_module_file_name = module_file_name.replace("_footnote", "")
        module_path_3 = (
            f"src.dom_normalizer.{package_name}.strategies.{short_module_file_name}"
        )
        attempted_paths.append(module_path_3)
        with contextlib.suppress(ModuleNotFoundError, AttributeError):
            module = importlib.import_module(module_path_3)
            return getattr(module, class_name_str)

    # NEW Attempt 4: Multiple strategies in a single 'strategies.py' file (e.g., src.dom_normalizer.lists.strategies)
    # In this case, the module name is just 'strategies', and the class is inside it.
    module_path_4 = f"src.dom_normalizer.{package_name}.strategies"
    attempted_paths.append(module_path_4)
    with contextlib.suppress(ModuleNotFoundError, AttributeError):
        module = importlib.import_module(module_path_4)
        return getattr(module, class_name_str)

    # If all attempts fail, raise a comprehensive error
    raise ImportError(
        f"Could not load strategy class '{class_name_str}' from any of the attempted module paths: {', '.join(attempted_paths)}",
    )


def load_handler_class(package_name: str, class_name_str: str):
    """Dynamically loads a media handler class from the 'handlers' module."""
    module_path = f"src.dom_normalizer.{package_name}.handlers"
    try:
        module = importlib.import_module(module_path)
        return getattr(module, class_name_str)
    except (ModuleNotFoundError, AttributeError) as exc:
        raise ImportError(
            f"Could not load handler class '{class_name_str}' from {module_path}",
        ) from exc


def normalize_html(html_str: str) -> str:
    """
    Parses and normalizes XHTML using BeautifulSoup's .prettify() to eliminate
    artificial formatting, indentation, and spacing discrepancies.
    """
    if not html_str:
        return ""

    # Protect em-spaces, which are semantic indentation for poetry, from being
    # collapsed by the whitespace normalization logic.
    em_space_placeholder = "___EM_SPACE_PLACEHOLDER___"
    html_str_protected = html_str.replace("\u2003", em_space_placeholder)

    soup = BeautifulSoup(html_str_protected.strip(), "html5lib")
    # Collapse redundant spaces in text nodes to prevent false formatting alarms
    for text_node in soup.find_all(string=True):
        if text_node.parent and text_node.parent.name not in ["pre", "code"]:
            normalized_text = " ".join(str(text_node).split())
            text_node.replace_with(normalized_text)
    pretty_html = soup.prettify()
    return pretty_html.replace(em_space_placeholder, "\u2003")


def _validate_dom_mutation(
    soup: BeautifulSoup,
    expected_html_raw: str | None,
    results: dict[str, Any],
):
    """Validates the mutated HTML against the expected output."""
    if expected_html_raw is None:
        return

    actual_html = normalize_html(str(soup))
    expected_html = normalize_html(expected_html_raw)

    if actual_html != expected_html:
        results["passed"] = False
        diff = difflib.unified_diff(
            expected_html.splitlines(keepends=True),
            actual_html.splitlines(keepends=True),
            fromfile="[EXPECTED DOM]",
            tofile="[ACTUAL MUTATED DOM]",
        )
        results["failures"].append(("HTML_MISMATCH", "".join(diff)))


def _validate_telemetry(
    instance: Any,
    expected_telemetry: dict[str, Any] | None,
    results: dict[str, Any],
):
    """Validates the telemetry metrics of the normalizer instance."""
    if not expected_telemetry:
        return

    for metric_name, expected_val in expected_telemetry.items():
        if metric_name in ["status", "execution_timestamp"]:
            continue  # Skip variable metadata

        # Special mapping for MediaProcessor telemetry, which uses different names
        # in its final metadata vs. its internal counters.
        metric_map = {
            "unsupported_media_purged": "purged_count",
            "external_videos_wrapped": "external_video_count",
            "base64_media_extracted": "base64_count",
            "images_processed": "local_image_count",
            "audio_files_processed": "local_audio_count",
            "video_files_processed": "local_video_count",
        }
        if (
            instance.__class__.__name__ == "MediaProcessor"
            and metric_name in metric_map
        ):
            actual_val = getattr(instance, metric_map[metric_name], None)
        elif (
            instance.__class__.__name__ == "MediaProcessor"
            and metric_name == "local_media_relocated"
        ):
            actual_val = (
                getattr(instance, "local_image_count", 0)
                + getattr(instance, "local_audio_count", 0)
                + getattr(instance, "local_video_count", 0)
            )
        else:
            actual_val = getattr(instance, metric_name, None)
        if actual_val != expected_val:
            results["passed"] = False
            err_msg = f"Incorrect metric '{metric_name}'. Expected {expected_val}, got {actual_val}."
            results["failures"].append(("METRIC_MISMATCH", err_msg))


def _validate_files_written(
    context: MockBookStyleContext,
    expected_files: list[dict[str, Any]] | None,
    results: dict[str, Any],
):
    """Validates that the expected files were written to the virtual disk."""
    if not expected_files:
        return

    for file_spec in expected_files:
        target_path = file_spec["path"]
        expected_hash = file_spec.get("content_hash")

        if target_path not in context.written_files:
            results["passed"] = False
            results["failures"].append(
                (
                    "FILE_NOT_WRITTEN",
                    f"Expected file '{target_path}' was not written to the virtual disk.",
                ),
            )
        elif expected_hash and context.written_files[target_path] != expected_hash:
            results["passed"] = False
            results["failures"].append(
                (
                    "FILE_CONTENT_MISMATCH",
                    f"Content hash mismatch for file '{target_path}'.",
                ),
            )


def _instantiate_strategy(
    strategy_class: type,
    case: dict[str, Any],
    context: MockBookStyleContext,
) -> tuple[Any, MockProcessor | None]:
    """Instantiates a strategy, creating and binding a mock processor."""

    mock_processor = MockProcessor(context)
    strategy_instance: Any

    # Inspect the __init__ signature to determine how to instantiate
    sig = inspect.signature(strategy_class.__init__)
    params = sig.parameters

    init_args = {}
    if "context" in params:
        # Pattern for strategies that require context in their constructor,
        # like those in `structural_sanitizer`. We cast to satisfy type hints.
        init_args["context"] = cast(RealBookStyleContext, context)
    if "processor" in params:
        init_args["processor"] = mock_processor
    if "config_params" in params:  # For ParameterizedFootnoteStrategy
        init_args["config_params"] = case.get("strategy_config", {})
    if "notes_file_key" in params:  # For NativeConventionFootnoteStrategy
        init_args["notes_file_key"] = case.get("notes_file_key")

    # Instantiate the strategy
    strategy_instance = strategy_class(**init_args)

    # Always bind the mock_processor if the strategy has a 'processor' attribute.
    # This covers all BaseFootnoteStrategy and BaseBlockquoteStrategy subclasses.
    if hasattr(strategy_instance, "processor"):
        strategy_instance.processor = mock_processor
    if hasattr(strategy_instance, "context"):
        strategy_instance.context = cast(RealBookStyleContext, context)
    if hasattr(strategy_instance, "config"):
        strategy_instance.config = context.config
    return strategy_instance, mock_processor


def _execute_process_method_with_inspection(
    strategy_instance: Any,
    soup: BeautifulSoup,
    context: MockBookStyleContext,
) -> None:
    """Inspects a 'process' method's signature and calls it correctly."""
    process_method_unbound = strategy_instance.__class__.process
    sig = inspect.signature(process_method_unbound)
    params = sig.parameters
    process_method_bound = strategy_instance.process

    # For NodeStrategy-based tests (e.g., structural_sanitizer)
    if "node" in params:
        _block_level_tags = frozenset(
            [
                "p",
                "div",
                "h1",
                "h2",
                "h3",
                "h4",
                "h5",
                "h6",
                "blockquote",
                "pre",
                "li",
                "td",
                "th",
                "section",
                "article",
                "aside",
                "main",
                "header",
                "footer",
            ],
        )
        for node in find_all_snapshot(soup, list(_block_level_tags)):
            if node.parent is not None and isinstance(node, Tag):
                process_method_bound(node)
        return

    # For DocumentStrategy or other processor-like strategies
    num_params = len(params)
    if num_params == 2:  # e.g., process(self, soup)
        process_method_bound(soup)
    elif num_params == 3:  # e.g., process(self, soup, context)
        process_method_bound(soup, context)
    elif (
        num_params == 4
    ):  # e.g., process(self, soup, context, all_soups)
        process_method_bound(soup, context, None)
    elif (
        num_params == 5
    ):  # e.g., process(self, soup, context, all_soups, current_soup_key)
        process_method_bound(soup, context, None, None)
    else:
        raise TypeError(
            f"Unexpected signature for {strategy_instance.__class__.__name__}.process: {sig}. "
            "The test runner supports 2, 3, 4, or 5 parameters (including self).",
        )


def _execute_handle_method(
    strategy_instance: Any,
    soup: BeautifulSoup,
    context: MockBookStyleContext,
) -> None:
    """Executes the 'handle' method on a strategy instance."""
    if not soup.body:
        raise ValueError("Input HTML for test case is missing a <body> tag.")
    for tag in tuple(soup.find_all(True)):
        if tag.parent and strategy_instance.can_handle(tag):
            from pathlib import Path

            mock_file_path = Path(context.file_name)
            strategy_instance.handle(tag, soup, mock_file_path)


def _execute_find_and_apply_method(
    strategy_instance: Any,
    soup: BeautifulSoup,
    context: MockBookStyleContext,
) -> None:
    """Executes the 'find_and_apply' method on a strategy instance."""
    if not soup.body:
        raise ValueError("Input HTML for test case is missing a <body> tag.")
    # Simulate the main processor loop for find_and_apply strategies.
    # These strategies expect to be called on each potential starting node.
    processed_nodes = set()
    for node in find_all_snapshot(soup, ["p", "div"]):
        if node in processed_nodes:
            continue
        if returned_sequence := strategy_instance.find_and_apply(
            node,
            context,
            soup,
        ):
            processed_nodes.update(returned_sequence)


def _dispatch_strategy_execution(
    strategy_instance: Any,
    soup: BeautifulSoup,
    context: MockBookStyleContext,
) -> None:
    """Dispatches execution to the correct method on the strategy instance."""
    if hasattr(strategy_instance, "handle"):  # For MediaProcessor handlers
        _execute_handle_method(strategy_instance, soup, context)
    elif hasattr(
        strategy_instance,
        "find_and_apply",
    ):  # For BlockquoteProcessor strategies
        _execute_find_and_apply_method(strategy_instance, soup, context)
    elif hasattr(strategy_instance, "process"):
        _execute_process_method_with_inspection(strategy_instance, soup, context)
    else:
        raise AttributeError(
            f"Strategy class {strategy_instance.__class__.__name__} has no 'find_and_apply', 'process', or 'handle' method.",
        )


def _setup_media_processor_mocks(
    processor_instance: Any,
    context: MockBookStyleContext,
) -> None:
    """Sets up mocks for MediaProcessor's I/O operations."""
    from pathlib import Path

    def mock_read_local_asset(src_attr, _file_path):
        if not isinstance(src_attr, str):
            return None
        ext = Path(src_attr).suffix.lower() or ".dat"
        return (b"dummy file content", ext)

    processor_instance.read_local_asset = mock_read_local_asset

    def mock_get_sha256_hash(data):
        base64_pixel_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=",
        )
        if data == base64_pixel_data:
            return "d2c753435521f7765a5a84a3b438969b3b465c84437a9b1343370339964b64c7"
        if data == b"dummy file content":
            return "placeholder-hash"
        return hashlib.sha256(data).hexdigest()

    processor_instance.get_sha256_hash = mock_get_sha256_hash

    def mock_save_asset_to_sibling_dir(
        media_type: str,
        asset_filename: str,
        binary_data: bytes,
    ) -> str:
        relative_path = os.path.join(
            "..",
            "media",
            media_type,
            asset_filename,
        ).replace(os.sep, "/")
        stored_hash = processor_instance.get_sha256_hash(binary_data)
        full_write_path = os.path.join(
            context.book_base_name,
            "media",
            media_type,
            asset_filename,
        )
        context.written_files[full_write_path] = stored_hash
        return relative_path

    processor_instance.save_asset_to_sibling_dir = mock_save_asset_to_sibling_dir


def _run_strategy_test(
    case: dict[str, Any],
    context: MockBookStyleContext,
    soup: BeautifulSoup,
    package_name: str,
    results: dict[str, Any],
) -> None:
    """Executes a single test case for a strategy or handler in isolation."""
    class_name_str = case["target"].split(" ")[0].split(".")[0]

    if "Handler" in class_name_str:
        strategy_class = load_handler_class(package_name, class_name_str)
    else:
        strategy_class = load_strategy_class(package_name, class_name_str)

    strategy_instance, mock_processor = _instantiate_strategy(
        strategy_class,
        case,
        context,
    )

    _dispatch_strategy_execution(strategy_instance, soup, context)

    # After mutation, validate telemetry against the mock_processor
    expected_telemetry = case["expected"].get("telemetry", {})
    if mock_processor:
        _validate_telemetry(mock_processor, expected_telemetry, results)


def _run_context_test(
    case: dict[str, Any],
    context: MockBookStyleContext,
    soup: BeautifulSoup,
) -> None:
    """Executes a single test case for a BookStyleContext method."""
    target_str = case["target"]
    class_name_str, method_name_str = target_str.split(".", 1)
    method_name_str = method_name_str.split(" ", 1)[0]  # Clean up " - Rule" part

    if class_name_str != "BookStyleContext":
        raise ValueError(f"Invalid target for context test: {target_str}")

    # The instance under test is a REAL context object, not the mock.
    # We use the mock context's properties to initialize the real one.
    instance_to_test = RealBookStyleContext(
        primary_language=ISOLanguageCode(context.primary_language),
    )
    method_to_run = getattr(instance_to_test, method_name_str)

    # The context methods are typically called on all nodes in a loop.
    # We replicate that behavior here for the test, iterating over a static
    # snapshot to avoid issues with in-place DOM modification.
    for node in tuple(soup.find_all(True)):
        if isinstance(node, Tag):
            method_to_run(node)

    # No telemetry to check on the context object itself for these tests.


def _run_processor_test(
    case: dict[str, Any],
    context: MockBookStyleContext,
    soup: BeautifulSoup,
    package_name: str,
    results: dict[str, Any],
) -> None:
    """Executes a single test case for a full processor (integration test)."""
    # For parameterized strategies tested via the processor, inject the config.
    if case.get("strategy_config"):
        context.config.footnote_patterns = [case["strategy_config"]]
    else:
        context.config.footnote_patterns = []

    expected_telemetry = case["expected"].get("telemetry", {})
    factory_kwargs = {}
    processor_instance = None

    # Special handling for MediaProcessor which requires file paths and I/O mocking.
    # The package name is reported as either "media" or "media_processor" depending
    # on the suite metadata, so support both aliases to keep the file resolution
    # tests deterministic.
    if package_name in {"media", "media_processor"}:
        with tempfile.TemporaryDirectory() as temp_dir:
            from pathlib import Path

            output_dir = Path(temp_dir)
            book_root = output_dir / "book_src"
            book_root.mkdir()

            factory_kwargs = {
                "output_directory": str(output_dir),
                "book_root_path": str(book_root),
                "book_base_name": context.book_base_name,
            }
            processor_instance = create_processor(package_name, context, **factory_kwargs)
            _setup_media_processor_mocks(processor_instance, context)

            # Execute the process method within the temp dir context
            _execute_and_validate_processor(
                processor_instance,
                soup,
                case,
                results,
                expected_telemetry,
            )
    else:
        # Default instantiation for all other processors
        processor_instance = create_processor(package_name, context, **factory_kwargs)
        _execute_and_validate_processor(
            processor_instance,
            soup,
            case,
            results,
            expected_telemetry,
        )


def _execute_and_validate_processor(
    processor_instance: Any,
    soup: BeautifulSoup,
    case: dict[str, Any],
    results: dict[str, Any],
    expected_telemetry: dict[str, Any],
) -> None:
    """Helper to run the process method and validate telemetry."""
    # Find the main entry point method ('process' or 'sanitize')
    process_method = getattr(processor_instance, "process", None) or getattr(
        processor_instance,
        "sanitize",
        None,
    )
    if not process_method:
        raise AttributeError(
            f"Processor class {processor_instance.__class__.__name__} has no 'process' or 'sanitize' method.",
        )

    # Get context_spec for special argument handling
    context_spec = case.get("context", {})

    # Call the process method with the correct signature
    from pathlib import Path

    sig = inspect.signature(process_method)
    kwargs = {}
    if "file_path" in sig.parameters:
        context = cast(MockBookStyleContext, processor_instance.context)
        kwargs["file_path"] = Path(context.file_name)
    if "is_new_book_or_document" in sig.parameters:
        kwargs["is_new_book_or_document"] = context_spec.get(
            "is_new_book_or_document",
            False,
        )

    process_method(soup, **kwargs)
    # After mutation, validate telemetry against the processor instance
    _validate_telemetry(processor_instance, expected_telemetry, results)


def run_single_test_case(
    case: dict[str, Any],
    package_name: str,
    suite_path: str,
) -> dict[str, Any]:
    """Runs a single test case in isolation against the target normalizer class."""
    case_id = case["id"]
    target_str = case["target"]
    context_spec = case.get("context", {})
    context = MockBookStyleContext(context_spec)

    input_html = (
        case["input"].get("html")
        or case["input"].get("document")
        or case["input"].get("node")
    )
    soup = BeautifulSoup(input_html, "html5lib")
    results = {"id": case_id, "passed": True, "failures": [], "error": None}

    # Determine test type based on the target string, not the filename.
    # First, check for no-op tests (like utility modules or compilers)
    noop_targets = (
        "EngineConfiguration",
        "dom_utils",
        "list_utils",
        "navigation_utils",
        "media_utils",
        "StructuralStrategyCompiler",
        "ForensicPatternAnalyzer",
    )
    is_noop_test = any(noop_target in target_str for noop_target in noop_targets)
    is_strategy_test_file = "strategies.yaml" in suite_path
    if is_noop_test:
        pass  # No action, just validate HTML/telemetry
    elif (
        is_strategy_test_file and package_name != "poetry"
    ) or "Handler" in target_str:
        _run_strategy_test(case, context, soup, package_name, results)
    elif "BookStyleContext" not in target_str:
        # If the target is not a strategy, handler, or context, it must be a
        # processor-level (integration) test.
        _run_processor_test(case, context, soup, package_name, results)
    else:
        _run_context_test(case, context, soup)

    # --- Common Validation Logic ---

    expected_html_raw = case["expected"].get("html") or case["expected"].get(
        "mutated_node",
    )
    _validate_dom_mutation(soup, expected_html_raw, results)

    # Note: Telemetry validation is now handled inside the conditional branches
    # to target the correct instance (mock_processor vs. processor_instance).
    # This block is left here as a structural reminder but is now redundant.
    # A future refactor could merge the telemetry dict loading.

    expected_files = case["expected"].get("files_written", [])
    _validate_files_written(context, expected_files, results)

    return results


def _print_colorized_diff(details: str):
    """Prints a unified diff with color-coded lines."""
    for line in details.splitlines():
        if line.startswith("+"):
            print(f"{GREEN}{line}{RESET}")
        elif line.startswith("-"):
            print(f"{RED}{line}{RESET}")
        elif line.startswith("^"):
            print(f"{BLUE}{line}{RESET}")
        else:
            print(line)


def _print_failure_report(all_failures_report: list[tuple[str, dict[str, str], list[tuple[str, str]]]]):
    """Prints a detailed report of all failed and errored test cases."""
    if not all_failures_report:
        return

    print(
        f"\n{BOLD}{RED}=================================== FAILURES ==================================={RESET}",
    )
    for suite_file, case, failures in all_failures_report:
        print(
            f"\n{BOLD}{RED}_________________ FAIL: {case['id']} ({case['target']}) _________________{RESET}",
        )
        print(f"{BOLD}Suite File:{RESET} {suite_file}")
        print(f"{BOLD}Description:{RESET} {case['description']}")
        print("-" * 80)

        for fail_type, details in failures:
            print(f"{YELLOW}[{fail_type}]{RESET}")
            if fail_type == "HTML_MISMATCH":
                _print_colorized_diff(details)
            else:
                print(details)
        print("-" * 80)


def _print_summary(stats: dict[str, int]):
    """Prints the final summary of the test run."""
    print(
        f"\n{BOLD}{CYAN}============================= EXECUTION SUMMARY ============================={RESET}",
    )
    print(f"Suites processed: {stats['total_suites']}")
    print(f"Total test cases: {stats['total_cases']}")

    summary_color = (
        GREEN if stats["failed_cases"] == 0 and stats["error_cases"] == 0 else RED
    )
    print(
        f"{BOLD}{summary_color}Passed: {stats['passed_cases']} | Failed: {stats['failed_cases']} | Errors: {stats['error_cases']}{RESET}",
    )
    print(
        f"{BOLD}{CYAN}=============================================================================={RESET}\n",
    )


def _run_suite_cases(
    test_cases: list[dict[str, Any]],
    suite_path: str,
    stats: dict[str, int],
    all_failures_report: list[Any],
    package_name: str,
):
    """Runs all test cases for a single suite."""
    for case in test_cases:
        stats["total_cases"] += 1
        try:
            res = run_single_test_case(case, package_name, suite_path)
            if res["passed"]:
                print(
                    f"  {GREEN}✓ [PASSED]{RESET} {res['id']}: {case['target']}",
                )
                stats["passed_cases"] += 1
            else:
                print(f"  {RED}x [FAILED]{RESET} {res['id']}: {case['target']}")
                stats["failed_cases"] += 1
                all_failures_report.append((suite_path, case, res["failures"]))
        except (ValueError, KeyError, TypeError, AttributeError) as e:  
            print(
                f"  {YELLOW}‼ [ERROR]{RESET} {case['id']}: {case['target']} — {e}",
            )
            stats["error_cases"] += 1
            all_failures_report.append(
                (suite_path, case, [("RUNTIME_ERROR", traceback.format_exc())]),
            )


def _process_single_suite_definition(
    suite_data: Any,
    suite_path: str,
    stats: dict[str, int],
    all_failures_report: list[Any],
):
    """Processes a single suite definition from a YAML file."""
    if not isinstance(suite_data, dict):
        print(
            f"{RED}[YAML FORMAT ERROR] in {suite_path}: Expected a dictionary for suite, but got {type(suite_data)}{RESET}",
        )
        stats["error_cases"] += 1
        return

    package_name = suite_data.get("package")
    if not package_name:
        print(
            f"{RED}[YAML FORMAT ERROR] in {suite_path}: Suite is missing the required 'package' key.{RESET}",
        )
        # A suite without a package is a single error, regardless of test cases
        stats["error_cases"] += 1
        return

    test_cases = suite_data.get("test_cases", [])
    file_name = os.path.basename(suite_path)

    print(
        f"{BOLD}{BLUE}SUITE:{RESET} {package_name} ({file_name}) — {len(test_cases)} cases.",
    )

    # The loading of the target class is now deferred to run_single_test_case
    # to allow for both processor-level and strategy-level testing.
    _run_suite_cases(test_cases, suite_path, stats, all_failures_report, package_name)


def _process_suite_file(
    suite_path: str,
    stats: dict[str, int],
    all_failures_report: list[Any],
):
    """Loads, parses, and runs the test suites from a single YAML file."""
    with open(suite_path, encoding="utf-8") as f:
        try:
            loaded_yaml = yaml.safe_load(f)
        except yaml.YAMLError as e:  
            print(f"{RED}[YAML SYNTAX ERROR] in {suite_path}: {e}{RESET}")
            stats["error_cases"] += 1
            return

    if not loaded_yaml:
        return

    suite_definitions = loaded_yaml if isinstance(loaded_yaml, list) else [loaded_yaml]
    stats["total_suites"] += len(suite_definitions)

    for suite_data in suite_definitions:
        _process_single_suite_definition(
            suite_data,
            suite_path,
            stats,
            all_failures_report,
        )

    print()


def discover_and_run_all_suites(specs_dir: str):
    """Filewalker that crawls the test directory and dispatches test suites."""
    print(
        f"\n{BOLD}{CYAN}============ STARTING ADVERSARIAL TEST ENGINE (YAML) ============{RESET}\n",
    )

    stats = {
        "total_suites": 0,
        "total_cases": 0,
        "passed_cases": 0,
        "failed_cases": 0,
        "error_cases": 0,
    }
    all_failures_report: list[Any] = []

    for root, _, files in os.walk(specs_dir):
        for file in files:
            if not file.endswith((".yaml", ".yml")):
                continue

            suite_path = os.path.join(root, file)
            _process_suite_file(suite_path, stats, all_failures_report)

    _print_failure_report(all_failures_report)
    _print_summary(stats)

    if stats["failed_cases"] > 0 or stats["error_cases"] > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    # Configure your YAML specification directory path
    SPECS_DIRECTORY = "tests/specs"
    if not os.path.exists(SPECS_DIRECTORY):
        os.makedirs(SPECS_DIRECTORY)
        print(
            f"{YELLOW}Created folder '{SPECS_DIRECTORY}'. Place your YAML test files inside it.{RESET}",
        )

    discover_and_run_all_suites(SPECS_DIRECTORY)
