"""
Core infrastructure and molecular layout matching engine for DOM normalization.

This package provides the foundational components for the entire `dom_normalizer`
library, including data structures for context management, strict type contracts
for data integrity, and a suite of robust utility functions for DOM analysis and
mutation.

Key components include:
  - `BookStyleContext`: A thread-isolated class that parses CSS to build a
    structural profile of a book, enabling style-based element identification.
  - `ISOLanguageCode`: A value object ensuring all language codes conform to the
    ISO 639-1 standard.
  - `EngineConfiguration`: A dataclass for global, immutable settings.
  - `PipelineStatus`: An enumeration for reporting the outcome of a processing stage.
  - Utility Constants: A collection of constants for common tasks like identifying
    page markers (`PAGE_MARKER_RX`) or minimum list items (`MIN_VIABLE_LIST_ITEMS`).

Concurrency Contract: This library is designed to be thread-safe by avoiding
shared mutable state. It does not provide synchronization primitives; the
orchestrating application is responsible for managing concurrent access to
external resources.
"""

from .config import EngineConfiguration
from .config_loader import get_book_specific_config, load_global_config
from .constants import (
    BLOCKQUOTE_ELEMENT_CLASS,
    BOLD_ELEMENT_CLASS,
    CODE_CLASSES,
    DIALOGUE_DASH_RX,
    FLOATING_ELEMENT_CLASS,
    ITALIC_ELEMENT_CLASS,
    PAGE_MARKER_RX,
    POETIC_MID_PUNCTUATION,
    POETIC_TERMINAL_PUNCTUATION,
    get_speaker_label_rx,
)
from .context import BookStyleContext
from .lang_codes import ISOLanguageCode
from .status import PipelineStatus

__all__ = [
    "BLOCKQUOTE_ELEMENT_CLASS",
    "BOLD_ELEMENT_CLASS",
    "CODE_CLASSES",
    "DIALOGUE_DASH_RX",
    "FLOATING_ELEMENT_CLASS",
    "ITALIC_ELEMENT_CLASS",
    "PAGE_MARKER_RX",
    "POETIC_MID_PUNCTUATION",
    "POETIC_TERMINAL_PUNCTUATION",
    "BookStyleContext",
    "EngineConfiguration",
    "ISOLanguageCode",
    "PipelineStatus",
    "get_speaker_label_rx",
    "load_global_config",
    "get_book_specific_config",
]
