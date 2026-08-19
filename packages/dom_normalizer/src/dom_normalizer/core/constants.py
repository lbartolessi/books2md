"""A centralized module for core constants used across the normalization pipeline."""

import re
from typing import Final

from .config import EngineConfiguration

# --- Page Marker Patterns ---
# Spanish page markers (e.g., "pág.", "página").
_SPANISH_PAGE_MARKERS: Final[str] = r"pág(?:ina)?\.?"

PAGE_MARKER_RX: Final[re.Pattern[str]] = re.compile(
    # This regex is intentionally strict, requiring the word "page" or a variant.
    # This avoids false positives on nodes containing only a number, which could
    # be legitimate content (e.g., a numbered list item).
    # Example matches: "Page 123", "pág. 123", "Página 123".
    rf"^(?:page|{_SPANISH_PAGE_MARKERS})\s+\d+$",
    re.IGNORECASE,
)

# --- Canonical Class Names ---
FLOATING_ELEMENT_CLASS: Final[str] = "floating-element"
BLOCKQUOTE_ELEMENT_CLASS: Final[str] = "blockquote-element"
ITALIC_ELEMENT_CLASS: Final[str] = "italic-element"
BOLD_ELEMENT_CLASS: Final[str] = "bold-element"

# --- Code-related Classes ---
CODE_CLASSES: Final[frozenset[str]] = frozenset(
    ["programlisting", "code-snippet", "source-code"],
)

# --- Poetry and Dialogue Detection ---

# This regex allows an optional opening quote mark before the dash to catch
# dialogue patterns like '—Hello' or "—Hello".
# Example matches: "—Hello", " — Hello", "«—Hola»".
DIALOGUE_DASH_RX: Final[re.Pattern[str]] = re.compile(
    r"^\s*[«“‹‘„\"\']?\s*[\u2014\u2013-]",  # NOSONAR
)

# Accented uppercase characters for Latin-based languages (e.g., Spanish, French).
_LATIN_ACCENTED_UPPER: Final[str] = "ÁÉÍÓÚÑÀÈÌÒÙÇ"


def get_speaker_label_rx(config: EngineConfiguration) -> re.Pattern[str]:
    """Generates a compiled regex for speaker labels based on configuration.

    Matches speaker labels in scripts (e.g., "HAMLET:", "JOHN.:", "ÉLODIE:").
    The length of the label is configurable.
    """
    return re.compile(
        rf"^\s*[A-Z{_LATIN_ACCENTED_UPPER}]{{{config.min_speaker_label_length},{config.max_speaker_label_length}}}[.:]\s*",
    )


# Punctuation that can appear mid-line in verse without implying a full stop.
# Used by enjambment detection heuristics.
POETIC_MID_PUNCTUATION: Final[frozenset[str]] = frozenset(
    {",", ";", ":", "-", "\u2014", "\u2013"},
)

# Punctuation that typically marks the end of a sentence or complete thought.
# Used by enjambment detection heuristics.
POETIC_TERMINAL_PUNCTUATION: Final[frozenset[str]] = frozenset({".", "!", "?"})
