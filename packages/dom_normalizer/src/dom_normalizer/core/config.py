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
    _LINGUA_MODULE = cast(Any, importlib.import_module("lingua"))
except ImportError:
    _LINGUA_MODULE = None

if _LINGUA_MODULE:
    # This will be the actual lingua.Language enum
    LANGUAGE: Any = cast(Any, getattr(_LINGUA_MODULE, "Language", None))
else:
    LANGUAGE = None


def _validate_lingua_enum_names(language_map: dict[str, str]) -> dict[str, str]:
    """Helper to validate that all enum names in the map exist in lingua.Language.

    This validation is specifically tied to the EngineConfiguration.language_enum_map
    setting, which is typically configured via the DOM_NORMALIZER_LANGUAGE_ENUM_MAP
    environment variable.
    """
    if not LANGUAGE:
        log.warning(
            "The 'lingua-python' library is not installed. Skipping validation "
            "of 'language_enum_map' / 'DOM_NORMALIZER_LANGUAGE_ENUM_MAP'. "
            "Please install it for full validation.",
        )
        return language_map

    if invalid_items := [
        (key, value)
        for key, value in language_map.items()
        if not hasattr(LANGUAGE, value)
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
        default=["youtube.com", "youtu.be", "vimeo.com"],
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
    # Poetry Normalizer settings
    poetry_em_to_indent_ratio: int = Field(
        default=1,
        gt=0,
        description="Ratio for converting 'em' units to indentation levels.",
    )
    poetry_px_to_em_ratio: int = Field(
        default=16,
        gt=0,
        description="Ratio for converting 'px' units to 'em' units for indentation.",
    )
    poetry_percent_to_indent_ratio: int = Field(
        default=5,
        gt=0,
        description="Ratio for converting '%' units to indentation levels.",
    )
    poetry_nbsp_to_indent_ratio: int = Field(
        default=2,
        gt=0,
        description="Number of non-breaking spaces considered as one indentation level.",
    )
    poetry_max_words_for_enjambment: int = Field(
        default=50,
        gt=0,
        description="Maximum words in a line to be considered for enjambment analysis.",
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
