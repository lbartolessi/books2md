"""Manages global execution engine parameters using Pydantic Settings.

This module defines the `EngineConfiguration` class, which centralizes all
high-level configuration for the normalization pipeline. It uses Pydantic's
`BaseSettings` to load configuration from environment variables or a .env file,
ensuring that settings are consistent and read-only during execution.
"""

import importlib
import logging
from typing import Any, cast

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

log = logging.getLogger(__name__)

# Attempt to import lingua for validation, but allow the app to run without it.
try:
    _lingua_module = cast(Any, importlib.import_module("lingua"))
except ImportError:
    _lingua_module = None

if _lingua_module:
    # This will be the actual lingua.Language enum
    LinguaLanguage: Any = cast(Any, getattr(_lingua_module, "Language", None))
else:
    LinguaLanguage = None


def _validate_lingua_enum_names(language_map: dict[str, str]) -> dict[str, str]:
    """Helper to validate that all enum names in the map exist in lingua.Language.

    This validation is specifically tied to the EngineConfiguration.language_enum_map
    setting, which is typically configured via the DOM_NORMALIZER_LANGUAGE_ENUM_MAP
    environment variable.
    """
    if not LinguaLanguage:
        log.warning(
            "The 'lingua-python' library is not installed. Skipping validation "
            "of 'language_enum_map' / 'DOM_NORMALIZER_LANGUAGE_ENUM_MAP'. "
            "Please install it for full validation.",
        )
        return language_map

    if invalid_items := [
        (key, value)
        for key, value in language_map.items()
        if not hasattr(LinguaLanguage, value)
    ]:
        invalid_keys = [key for key, _ in invalid_items]
        invalid_values = [value for _, value in invalid_items]

        raise ValueError(
            "Invalid lingua.Language enum names found in "
            "EngineConfiguration.language_enum_map / "
            "DOM_NORMALIZER_LANGUAGE_ENUM_MAP. "
            f"Invalid keys: {', '.join(sorted(invalid_keys))}. "
            f"Invalid enum names: {', '.join(sorted(invalid_values))}. "
            "Please fix the DOM_NORMALIZER_LANGUAGE_ENUM_MAP setting so that all "
            "values match members of lingua.Language.",
        )
    return language_map


class EngineConfiguration(BaseSettings):
    """Manages global execution engine parameters using Pydantic Settings.

    This class centralizes all high-level configuration for the
    normalization pipeline, ensuring that settings are consistent and read-only
    during execution by loading them from environment variables or a .env file.
    It uses a prefix to avoid collisions in a multi-library environment.

    The default values represent a balanced configuration for general-purpose
    document processing. They can be overridden via environment variables
    (e.g., `DOM_NORMALIZER_INITIAL_HEADING_LEVEL=2`).

    Attributes:
        initial_heading_level: The starting level for recovered headings (e.g., 1 for `<h1>`).
        allow_heading_downlevels: Whether to allow heading levels to decrease (e.g., h3 -> h2).
        lingua_low_memory_mode: Enables low-memory mode for the `lingua` language detector.
        structural_registry_path: Path to the JSON file for structural patterns.
        footnote_registry_path: Path to the JSON file for footnote patterns.
        footnote_patterns: A list of footnote pattern configurations.
        min_pattern_length: Prefix-length pre-filter for footnote isomorphism detection.
        br_density_threshold: Threshold for detecting poetic content based on `<br>` tag density.
        dialogue_exclusion_threshold: Proportion of dialogue lines to exclude a block from poetry processing.
        enjambment_ratio_threshold: Threshold for detecting enjambment in potential poetic content.
        dense_container_tags: Tags that mark a container as having dense primary content.
        dense_container_heading_tags: Heading tags used to detect dense content containers.
        language_enum_map: Mapping of ISO 639-1 codes to `lingua-python` Language enum names.
        supported_languages: A computed list of languages supported for detection.
        external_video_domains: A list of domains identified as external video hosts.
        poetic_classes_substrings: Substrings to identify poetic container classes.
        min_br_for_poetic_metrics: Minimum `<br>` tags for a block to be considered for poetic metrics.
        max_avg_words_per_line_poetic: Maximum average words per line for a block to be poetic.
        poetry_em_to_indent_ratio: Ratio for converting 'em' units to indentation levels in poetry.
        poetry_px_to_em_ratio: Ratio for converting 'px' units to 'em' units for poetry indentation.
        poetry_percent_to_indent_ratio: Ratio for converting '%' units to indentation levels in poetry.
        poetry_nbsp_to_indent_ratio: Number of non-breaking spaces for one indentation level in poetry.
        poetry_max_words_for_enjambment: Maximum words in a line for enjambment analysis.
    """

    model_config = SettingsConfigDict(env_prefix="DOM_NORMALIZER_")
    initial_heading_level: int = 1
    allow_heading_downlevels: bool = True
    lingua_low_memory_mode: bool = False
    structural_registry_path: str = "config/structural_patterns.json"
    footnote_registry_path: str = "config/footnote_patterns.json"
    footnote_patterns: list[dict[str, Any]] = Field(default_factory=list)
    min_pattern_length: int = (
        2  # Prefix-length pre-filter for footnote isomorphism detection.
    )
    # A heuristic gate to reduce candidate noise before full validation.
    br_density_threshold: float = 60.0  # Threshold for detecting poetic content based on `<br>` tag density. (Provisional)
    dialogue_exclusion_threshold: float = (
        0.40  # Proportion of dialogue lines to exclude a block from poetry processing.
    )
    enjambment_ratio_threshold: float = 0.60  # Threshold for detecting enjambment in potential poetic content. (Provisional)
    # Tags that, if found within a candidate, mark it as a dense primary content container.
    dense_container_tags: list[str] = ["body", "main", "article"]
    # Heading tags used to detect dense primary content containers.
    dense_container_heading_tags: list[str] = ["h1", "h2", "h3"]
    language_enum_map: dict[str, str] = Field(
        default={
            "de": "GERMAN",
            "el": "GREEK",
            "en": "ENGLISH",
            "es": "SPANISH",
            "fr": "FRENCH",
            "it": "ITALIAN",
            "la": "LATIN",
            "pt": "PORTUGUESE",
        },
        description=(
            "Mapping of ISO 639-1 language codes to lingua-python Language enum names. "
            "Can be configured via the DOM_NORMALIZER_LANGUAGE_ENUM_MAP environment variable."
        ),
    )

    @field_validator("language_enum_map")
    @classmethod
    def validate_language_enum_map(cls, v: dict[str, str]) -> dict[str, str]:  # pylint: disable=unused-argument
        """Validates that all enum names in the map exist in lingua.Language."""
        return _validate_lingua_enum_names(v)

    @computed_field
    @property
    def supported_languages(self) -> list[str]:
        """Languages to be detected by the LanguageTagger.

        This is a computed property derived from the keys of `language_enum_map`
        to ensure that the list of supported languages and the enum mapping
        remain synchronized.

        Args:
            None

        Returns:
            A list of ISO 639-1 language code strings supported by the pipeline.
        """
        # Pylint reports a false positive here because it cannot infer the
        # type of a Pydantic model field within a computed property during
        # static analysis. The field is a dict at runtime.
        return list(self.language_enum_map.keys())  # pylint: disable=no-member

    external_video_domains: list[str] = Field(
        default=["youtube.com", "youtu.be", "vimeo.com", "dailymotion.com", "twitch.tv", "metacafe.com", "veoh.com", "bilibili.com", "rutube.ru", "ok.ru", "peer5.com", "vk.com", "mixcloud.com", "soundcloud.com", "bandcamp.com", "spotify.com", "apple.com", "netflix.com", "hulu.com", "disneyplus.com", "primevideo.com", "crunchyroll.com", "funimation.com"], 
        description=(
            "List of domains for external video hosts. The MediaProcessor uses these to build a "
            "regex that matches full hostnames (e.g., 'https://www.youtube.com/'), preventing "
            "partial matches like 'notyoutube.com'."
        ),
    )
    poetic_classes_substrings: list[str] = Field(
        default=["verse", "poem", "poesia", "poetic"],
        description="Substrings to identify poetic container classes.",
    )
    min_br_for_poetic_metrics: int = Field(
        default=2,
        gt=0,
        description="Minimum <br> tags for a block to be considered for poetic metrics.",
    )
    max_avg_words_per_line_poetic: int = Field(
        default=12,
        gt=0,
        description="Maximum average words per line for a block to be considered poetic.",
    )
    high_poetry_priority: bool = Field(
        default=False,
        description="Enables a global, heuristic scan for poetry, not just in blockquotes.",
    )
    high_priority_potential_tags: list[str] = Field(
        default_factory=lambda: ["div", "table", "p"],
        description="Tags to scan for poetry in high-priority mode.",
    )
    high_priority_attribute_hints: list[str] = Field(
        default_factory=lambda: ["poem", "poetry", "verse", "stanza", "lyrics"],
        description="Class/ID substrings that hint at poetry in high-priority mode.",
    )
    # Poetry Normalizer settings
    poetry_em_to_indent_ratio: float = Field(
        default=1.0,
        gt=0,
        description="Ratio for converting 'em' units to indentation levels.",
    )
    poetry_px_to_em_ratio: float = Field(
        default=0.0625,
        gt=0,
        description="Ratio for converting 'px' units to 'em' units for indentation.",
    )
    poetry_percent_to_indent_ratio: float = Field(
        default=0.5,
        gt=0,
        description="Ratio for converting '%' units to indentation levels.",
    )
    poetry_nbsp_to_indent_ratio: float = Field(
        default=0.5,
        gt=0,
        description="Number of non-breaking spaces considered as one indentation level.",
    )
    poetry_max_words_for_enjambment: int = Field(
        default=50,
        gt=0,
        description="Maximum words in a line to be considered for enjambment analysis.",
    )
    poetry_prose_word_count_multiplier: float = Field(
        default=2.0,
        gt=1.0,
        description="Multiplier for max_words_for_enjambment to determine if a paragraph is too long for poetry.",
    )
    poetry_max_nbsp_depth: int = Field(
        default=3,
        gt=0,
        description="Maximum DOM depth for NBSP-only lines to be considered indentation.",
    )
    poetry_indentation_tag_whitelist: tuple[str, ...] = Field(
        default=("span", "div", "p", "em", "strong"),
        description="Whitelisted tags for NBSP-based indentation detection.",
    )
    poetry_indentation_properties: tuple[str, ...] = Field(
        default=("margin-left", "padding-left", "text-indent"),
        description="CSS properties considered for poetry indentation calculation.",
    )
    poetry_indentation_units: tuple[str, ...] = Field(
        default=("em", "rem", "px", "%"),
        description="CSS units considered for poetry indentation calculation.",
    )
    min_viable_list_items: int = Field(
        default=2,
        gt=0,
        description="Minimum number of items for a sequence of nodes to be considered a list.",
    )
    list_unordered_prefix_rx: str = Field(
        default=r"^\s*([-\*\u2022\u25b6\u2013])\s+",
        description="Regex to detect unordered list item prefixes.",
    )
    list_ordered_prefix_rx: str = Field(
        default=r"^\s*(?:(\(?\d+[\.\)])|(\(?[a-zA-Z][\.\)])|(\(?[ivxIVX]+[\.\)]))\s*",
        description="Regex to detect ordered list item prefixes.",
    )
    list_class_keywords: frozenset[str] = Field(
        default=frozenset({"list", "item", "bullet", "calibre", "idgenparagraphstyle"}),
        description="Keywords to identify list-related CSS classes.",
    )
    list_complex_structure_tags: frozenset[str] = Field(
        default=frozenset({"ul", "ol", "table", "figure"}),
        description="Tags considered as complex structures that should not be wrapped inside a list item.",
    )
    list_level_mapping: dict[str, int] = Field(
        default={"bullet": 1, "numeric": 1, "alpha": 2, "roman": 3, "class_based": 1},
        description="Mapping of list prefix types to their default nesting level.",
    )
    min_indent_em_rem: float = Field(
        default=1.5,
        gt=0,
        description="Minimum indentation in 'em' or 'rem' to be considered significant.",
    )
    min_indent_px: int = Field(
        default=24,
        gt=0,
        description="Minimum indentation in 'px' to be considered significant.",
    )
    css_max_brace_depth: int = Field(
        default=50,
        gt=0,
        description="Maximum nesting depth for braces in CSS parsing to prevent stack overflows.",
    )
    css_max_scan_iterations: int = Field(
        default=1_000_000,
        gt=0,
        description="Maximum iterations for CSS scanning to prevent infinite loops on malformed CSS.",
    )
    min_speaker_label_length: int = Field(
        default=2, gt=0, description="Minimum character length for a speaker label."
    )
    # Navigation Purger settings
    tlcr_threshold: float = Field(
        default=0.85, gt=0.0, lt=1.0, description="Text-to-Link Character Ratio threshold for full-body purge."
    )
    protected_prose_classes: frozenset[str] = Field(
        default=frozenset({"prose", "editorial", "editorial-prose"}),
        description="Classes that, if present on a container, protect it from full-body purge.",
    )
    min_inline_toc_lines: int = Field(default=4, gt=0, description="Minimum consecutive lines to be considered a potential inline TOC block.")
    max_words_in_toc_airlock: int = Field(default=30, gt=0, description="Maximum words in a line to stop gathering a TOC block run.")
    min_tabular_index_rows: int = Field(default=2, gt=0, description="Minimum rows for a table to be considered a potential index.")
    max_chars_in_initial_column: int = Field(default=25, gt=0, description="Maximum character length for text in the first cell of a table row for index detection.")
    high_link_density_threshold: float = Field(default=0.7, gt=0.0, lt=1.0, description="Threshold for purging elements based on high link density.")
    max_speaker_label_length: int = Field(
        default=30, gt=0, description="Maximum character length for a speaker label."
    )
    # Footnote Forensic Analyzer settings
    footnote_donor_file_density_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Minimum ratio of note bodies in one file to classify it as a 'donor file'.",
    )
    footnote_symmetry_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum ratio of validated symmetric pairs to total callouts for a pattern to be considered valid.",
    )
    footnote_toc_heading_tags: frozenset[str] = Field(
        default=frozenset({"h1", "h2", "h3"}),
        description="Heading tags considered as TOC entries, to be ignored during footnote callout detection.",
    )
   # Navigation Utils settings
    min_toc_line_chars: int = Field(
        default=3, gt=0, description="Minimum character length for a line to be considered a potential TOC entry."
    )
    max_toc_line_chars: int = Field(
        default=70, gt=0, description="Maximum character length for a line to be considered a potential TOC entry."
    )
    checklist_start_numbers: tuple[int, ...] = Field(
        default=(0, 1), description="Starting numbers for a sequence to be considered a checklist and not a TOC."
    )
    # Media Utils settings
    mime_to_extension_map: dict[str, str] = Field(
        default={
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
        description="Centralized mapping of MIME types to file extensions.",
    )
    image_extension_aliases: frozenset[str] = Field(
        default=frozenset({".jpeg"}),
        description="Common aliases for image extensions.",
    )
    image_extension_alias_map: dict[str, str] = Field(
        default={".jpeg": ".jpg"},
        description="Mapping from alias extensions to their canonical counterparts.",
    )
    data_uri_prefix: str = Field(
        default="data:",
        description="Standard prefix for data URIs.",
    )

    @computed_field
    @property
    def audio_extensions(self) -> frozenset[str]:
        """Derived set of audio extensions for validation."""
        return frozenset(
            ext for mime, ext in self.mime_to_extension_map.items() if mime.startswith("audio/")
        )

    @computed_field
    @property
    def video_extensions(self) -> frozenset[str]:
        """Derived set of video extensions for validation."""
        return frozenset(
            ext for mime, ext in self.mime_to_extension_map.items() if mime.startswith("video/")
        )

    @computed_field
    @property
    def image_extensions(self) -> frozenset[str]:
        """Derived set of image extensions for validation."""
        return frozenset(
            ext for mime, ext in self.mime_to_extension_map.items() if mime.startswith("image/")
        ).union(self.image_extension_aliases)
    # Dom Utils settings
    media_tags: frozenset[str] = Field(
        default=frozenset(
            ["img", "svg", "video", "audio", "picture", "source", "canvas", "iframe", "math"]
        ),
        description="A curated set of tags considered to have renderable, non-textual content.",
    )
    block_level_tags: frozenset[str] = Field(
        default=frozenset(
            {
                "p", "div", "section", "article", "li", "ul", "ol", "dl", "dt", "dd",
                "table", "thead", "tbody", "tfoot", "tr", "td", "th", "figure",
                "header", "footer", "aside", "blockquote", "hr",
            }
        ),
        description="A curated set of tags considered block-level elements.",
    )
    semantic_attr_prefixes: tuple[str, ...] = Field(
        default=("aria-", "data-"),
        description="Prefixes of attributes considered semantically significant.",
    )
    semantic_attrs: frozenset[str] = Field(
        default=frozenset(["role"]),
        description="Specific attributes considered semantically significant.",
    )
    tag_identifier_attr_value_limit: int = Field(
        default=75, gt=0, description="Maximum length for attribute values in tag identifiers for logging."
    )
    # Table Normalizer settings
    min_div_table_rows: int = Field(
        default=2, gt=0, description="Minimum rows for a div-based structure to be considered a table."
    )
    min_div_table_cols: int = Field(
        default=2, gt=0, description="Minimum columns for a div-based structure to be considered a table."
    )
    header_promotion_threshold: float = Field(
        default=0.5, gt=0.0, lt=1.0, description="Ratio of bold cells in a row to promote it to a table header."
    )
    min_tables_for_fusion: int = Field(
        default=2, gt=0, description="Minimum number of tables required in a sequence for fusion attempts."
    )
    # Floating Element Processor settings
    density_exemption_char_threshold: int = Field(
        default=49, ge=0, description="Nodes with fewer characters than this are exempt from density checks."
    )
    standard_density_cap: float = Field(
        default=0.20, gt=0.0, lt=1.0, description="Standard character density ratio cap for non-primary content."
    )
    layout_enhanced_density_cap: float = Field(
        default=0.65, gt=0.0, lt=1.0, description="Enhanced density cap for nodes with explicit layout metadata."
    )
    min_document_chars_for_processing: int = Field(
        default=1, ge=0, description="Minimum document characters for floating element processing to run."
    )
    # Heading Normalizer settings
    max_sane_heading_length: int = Field(
        default=1000, gt=0, description="Maximum character length for a heading to be considered 'sane'."
    )
    max_heading_length: int = Field(
        default=150, gt=0, description="Maximum character length for a heading to be demoted."
    )
    max_link_density: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Maximum link density for a heading to be demoted."
    )
    bold_paragraph_heading_level: str = Field(
        default="h2", description="Target heading level for promoted bold paragraphs."
    )
    bold_promotion_requires_solitary_bold_tag: bool = Field(
        default=True, description="Heuristic for bold promotion: must be solitary child."
    )
    bold_promotion_requires_text_only_children: bool = Field(
        default=True, description="Heuristic for bold promotion: must contain only text."
    )
    heading_classes: dict[str, list[str]] = Field(
        default_factory=dict, description="Mapping of CSS classes to heading levels for promotion."
    )
    min_heading_level: int = Field(default=1, ge=1, le=6, description="Minimum valid HTML heading level (h1).")
    max_heading_level: int = Field(default=6, ge=1, le=6, description="Maximum valid HTML heading level (h6).")
    # Language Tagger settings
    min_lang_subtag_length: int = Field(default=2, gt=0, description="Minimum character length for a language subtag.")
    max_lang_subtag_length: int = Field(default=8, gt=0, description="Maximum character length for a language subtag.")
    # Math Processor settings
    min_latex_length: int = Field(
        default=3, gt=0, description="Minimum character length for a string to be considered valid LaTeX."
    )
    # Emphasis Normalizer settings
    max_flatten_passes: int = Field(
        default=10, gt=0, description="Maximum passes for flattening redundant emphasis tags to prevent infinite loops."
    )
    enable_contrastive_emphasis: bool = Field(
        default=False, description="Enables semantic reset for contrastive emphasis."
    )
    # Blockquote Processor settings
    blockquote_ttr_threshold: float = Field(
        default=3.0, description="Minimum Text-to-Tag Ratio for a block to be considered valid prose."
    )
    blockquote_anchor_density_threshold: float = Field(
        default=0.30, description="Maximum ratio of anchor text characters to total characters for a block."
    )
    blockquote_ttr_smoothing_factor: int = Field(
        default=1, description="Smoothing factor for TTR calculation to avoid division by zero."
    )
    epigraph_max_length: int = Field(
        default=300, description="Maximum character length for a block to be considered an epigraph."
    )
    epigraph_heading_proximity_limit: int = Field(
        default=4, description="How many previous siblings to check for a heading for an epigraph."
    )
    epigraph_heading_tags: frozenset[str] = Field(
        default=frozenset({"h1", "h2", "h3", "h4", "h5", "h6"}),
        description="Tags that should be treated as headings when scanning for epigraphs.",
    )
    epigraph_blocking_tags: frozenset[str] = Field(
        default=frozenset(
            {
                "p", "div", "section", "article", "aside", "main", "header", "footer", "nav",
                "ul", "ol", "dl", "figure", "figcaption", "picture", "video", "audio",
                "table", "blockquote", "pre", "form",
            }
        ),
        description="Tags that block an epigraph if they appear between a heading and a candidate quote.",
    )
    foreign_block_min_length: int = Field(
        default=25, description="Minimum character length for a paragraph to be considered a foreign block."
    )
    poetic_quote_min_lines: int = Field(
        default=2, description="Minimum number of lines for a sequence to be considered poetic."
    )
    poetic_quote_min_content_line_length: int = Field(
        default=2, description="Minimum character length for a line to be included in poetic statistical analysis."
    )
    poetic_quote_max_mean_length: int = Field(
        default=55, description="Maximum average line length for a poetic sequence."
    )
    poetic_quote_max_variance: float = Field(
        default=225.0, description="Maximum variance in line length for a poetic sequence."
    )
    prose_quote_min_indent_em: float = Field(
        default=1.5, description="Minimum indentation in 'em' for a prose quote."
    )
    prose_quote_min_indent_px: int = Field(
        default=20, description="Minimum indentation in 'px' for a prose quote."
    )
    prose_quote_min_indent_percent: int = Field(
        default=5, description="Minimum indentation in '%' for a prose quote."
    )
    prose_quote_min_indent_pt: float = Field(
        default=6.0, description="Minimum indentation in 'pt' for a prose quote."
    )
    prose_quote_min_indent_cm: float = Field(
        default=0.2, description="Minimum indentation in 'cm' for a prose quote."
    )
    prose_quote_px_per_em: float = Field(
        default=16.0, description="Conversion factor from px to em for prose quote indentation."
    )
    prose_quote_px_per_pt: float = Field(
        default=4.0 / 3.0, description="Conversion factor from px to pt for prose quote indentation."
    )
    prose_quote_px_per_cm: float = Field(
        default=96.0 / 2.54, description="Conversion factor from px to cm for prose quote indentation."
    )
    # Accessibility Normalizer settings
    accessibility_landmark_mapping: dict[str, str] = Field(
        default={"bibliography": "bibliography", "glossary": "glossary"},
        description="Mapping of ARIA doc-* roles to CSS classes for landmarks.",
    )
    accessibility_page_break_comment_format: str = Field(
        default=" page-break: {page_id} ",
        description="Format string for page break comments.",
    )
    accessibility_page_break_fallback_id: str = Field(
        default="unknown",
        description="Fallback ID for page breaks when no ID or title is found.",
    )
    accessibility_doc_role_prefix: str = Field(
        default="doc-", description="Prefix for ARIA doc-* roles."
    )
    accessibility_appendix_block_class: str = Field(
        default="appendix-block",
        description="Generic CSS class for appendix-like blocks (e.g., bibliography, glossary).",
    )
    accessibility_no_split_chunk_strategy: str = Field(
        default="no_split",
        description="Value for data-chunk-strategy to prevent splitting.",
    )
    # Blockquote Processor settings
    blockquote_paragraph_like_blocking_tags: frozenset[str] = Field(
        default=frozenset({"p", "div", "ul", "ol", "table", "blockquote"}),
        description="Tags that, if found inside a div, disqualify it from being 'paragraph-like'.",
    )
    # Poetry Normalizer settings
    poetry_block_class: str = Field(
        default="poetry-block",
        description="CSS class for the main poetry block wrapper.",
    )
    poetry_indent_char: str = Field(
        default="\u2003",
        description="Character used for representing one level of poetic indentation.",
    )
    poetry_indent_only_line_class: str = Field(
        default="poetry-indent-only-line",
        description="CSS class for spans that represent an indentation-only line.",
    )
    poetry_candidate_tags: list[str] = Field(
        default_factory=lambda: ["blockquote"],
        description="Initial candidate tags for poetry detection.",
    )
    poetry_high_priority_candidate_tags: list[str] = Field(
        default_factory=lambda: ["div", "table"],
        description="Additional candidate tags for high-priority poetry detection mode.",
    )
    # Math Processor settings
    math_related_tags: frozenset[str] = Field(
        default=frozenset({"math", "img", "svg"}),
        description="Tags considered to be math-related for block-level detection.",
    )
    math_simple_latex_cues: tuple[str, ...] = Field(
        default=("\\", "^", "_", "$"),
        description="Characters that suggest a string is simple LaTeX.",
    )
    math_block_class: str = Field(
        default="math-block", description="CSS class for block-level math wrappers."
    )
    math_inline_class: str = Field(
        default="math-inline", description="CSS class for inline math wrappers."
    )
    math_block_delimiters: tuple[str, str] = Field(
        default=("$$", "$$"), description="Delimiters for block-level LaTeX."
    )
    math_inline_delimiters: tuple[str, str] = Field(
        default=("$", "$"), description="Delimiters for inline LaTeX."
    )
    # Table Normalizer settings
    table_valid_parents: frozenset[str] = Field(
        default=frozenset({"tbody", "thead", "tfoot", "table"}),
        description="Valid parent tags for a <tr> element.",
    )
    table_orphan_tr_contexts: frozenset[str] = Field(
        default=frozenset({"body", "div", "section", "article", "main"}),
        description="Allowed contexts for wrapping orphan <tr> elements.",
    )
    # Lists Normalizer settings
    list_block_wrapper_tag: str = Field(
        default="div", description="Tag used to wrap reconstructed or sanitized lists."
    )
    list_block_wrapper_class: str = Field(
        default="list-block", description="CSS class for the list block wrapper."
    )
    # Structural Sanitizer settings
    sanitizer_block_level_tags: frozenset[str] = Field(
        default=frozenset(
            [
                "p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "pre",
                "li", "td", "th", "section", "article", "aside", "main", "header", "footer",
            ]
        ),
        description="Tags considered block-level for the main sanitizer loop.",
    )
    sanitizer_legacy_attrs_to_purge: frozenset[str] = Field(
        default=frozenset(["align", "bgcolor"]),
        description="Legacy presentational attributes to be purged.",
    )
    sanitizer_general_layout_props_to_purge: frozenset[str] = Field(
        default=frozenset(["margin-left", "padding-left", "float", "position", "background-color"]),
        description="Layout-related CSS properties to purge from general elements.",
    )
    sanitizer_blockquote_layout_props_to_purge: frozenset[str] = Field(
        default=frozenset(
            [
                "margin", "margin-top", "margin-right", "margin-bottom", "margin-left",
                "padding", "padding-top", "padding-right", "padding-bottom", "padding-left",
                "float", "position",
            ]
        ),
        description="Layout-related CSS properties to purge from blockquote elements.",
    )
    sanitizer_purgeable_empty_tags: frozenset[str] = Field(
        default=frozenset(
            [
                "p", "div", "span", "em", "strong", "i", "b", "u", "font", "a",
                "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "pre", "li", "td", "th",
            ]
        ),
        description="Tags eligible for removal if they are structurally empty.",
    )
    sanitizer_min_classes_for_sorting: int = Field(
        default=2,
        gt=0,
        description="Minimum number of classes a node must have to trigger sorting.",
    )
    # Table Normalizer settings
    # Floating Element Processor settings
    # Heading Normalizer settings
    # Language Tagger settings
    # Math Processor settings
    # Emphasis Normalizer settings
