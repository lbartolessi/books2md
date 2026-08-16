"""A centralized registry of ISO 639-1 language codes and a value object.

This module provides a single, authoritative source for the set of valid
two-letter ISO 639-1 language codes and an `ISOLanguageCode` value object to
enforce their correct usage throughout the application.

The list of codes is based on the official ISO 639-1 standard. For an accessible
reference, see: https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes

Attributes:
    ISO_639_1_CODES (Final[frozenset[str]]): An immutable set of all valid
        two-letter ISO 639-1 language codes.
"""

from typing import Final

ISO_639_1_CODES: Final[frozenset[str]] = frozenset(
    {
        "aa",
        "ab",
        "ae",
        "af",
        "ak",
        "am",
        "an",
        "ar",
        "as",
        "av",
        "ay",
        "az",
        "ba",
        "be",
        "bg",
        "bh",
        "bi",
        "bm",
        "bn",
        "bo",
        "br",
        "bs",
        "ca",
        "ce",
        "ch",
        "co",
        "cr",
        "cs",
        "cu",
        "cv",
        "cy",
        "da",
        "de",
        "dv",
        "dz",
        "ee",
        "el",
        "en",
        "eo",
        "es",
        "et",
        "eu",
        "fa",
        "ff",
        "fi",
        "fj",
        "fo",
        "fr",
        "fy",
        "ga",
        "gd",
        "gl",
        "gn",
        "gu",
        "gv",
        "ha",
        "he",
        "hi",
        "ho",
        "hr",
        "ht",
        "hu",
        "hy",
        "hz",
        "ia",
        "id",
        "ie",
        "ig",
        "ii",
        "ik",
        "io",
        "is",
        "it",
        "iu",
        "ja",
        "jv",
        "ka",
        "kg",
        "ki",
        "kj",
        "kk",
        "kl",
        "km",
        "kn",
        "ko",
        "kr",
        "ks",
        "ku",
        "kv",
        "kw",
        "ky",
        "la",
        "lb",
        "lg",
        "li",
        "ln",
        "lo",
        "lt",
        "lu",
        "lv",
        "mg",
        "mh",
        "mi",
        "mk",
        "ml",
        "mn",
        "mr",
        "ms",
        "mt",
        "my",
        "na",
        "nb",
        "nd",
        "ne",
        "ng",
        "nl",
        "nn",
        "no",
        "nr",
        "nv",
        "ny",
        "oc",
        "oj",
        "om",
        "or",
        "os",
        "pa",
        "pi",
        "pl",
        "ps",
        "pt",
        "qu",
        "rm",
        "rn",
        "ro",
        "ru",
        "rw",
        "sa",
        "sc",
        "sd",
        "se",
        "sg",
        "si",
        "sk",
        "sl",
        "sm",
        "sn",
        "so",
        "sq",
        "sr",
        "ss",
        "st",
        "su",
        "sv",
        "sw",
        "ta",
        "te",
        "tg",
        "th",
        "ti",
        "tk",
        "tl",
        "tn",
        "to",
        "tr",
        "ts",
        "tt",
        "tw",
        "ty",
        "ug",
        "uk",
        "ur",
        "uz",
        "ve",
        "vi",
        "vo",
        "wa",
        "wo",
        "xh",
        "yi",
        "yo",
        "za",
        "zh",
        "zu",
    },
)


class ISOLanguageCode(str):
    """An immutable value object that guarantees a valid ISO 639-1 language code.

    This class extends `str` and enforces a strict contract upon instantiation.
    It validates any given string against the complete official registry of
    two-letter ISO 639-1 codes, preventing context pollution from malformed or
    non-standard language identifiers. The comparison is case-insensitive, and
    the stored value is always lowercase.

    Input values are validated to be two-letter ASCII alphabetic codes before
    being checked against the registry.

    Attributes:
        _VALID_CODES (Final[frozenset[str]]): A class-level frozenset containing
            all valid ISO 639-1 codes for validation.

    Raises:
        TypeError: If the provided value is not a primitive string.
        ValueError: If the value is not a two-letter ASCII alphabetical string,
            or if it is well-formed but not an officially registered code.
    """

    _VALID_CODES: Final[frozenset[str]] = ISO_639_1_CODES
    _CODE_LENGTH: Final[int] = 2

    def __new__(cls, value: object) -> "ISOLanguageCode":
        """Creates a new instance of ISOLanguageCode after validation.

        Args:
            value: The value to be validated and instantiated as an
                ISOLanguageCode. Must be a primitive string.

        Returns:
            A new ISOLanguageCode instance if the value is valid.

        Raises:
            TypeError: If the provided value is not a primitive string.
            ValueError: If the value is not a well-formed or officially
                registered ISO 639-1 code.
        """
        if not isinstance(value, str):
            raise TypeError(
                f"Language code must be a primitive string. Received: {type(value)}",
            )

        if (clean_value := cls._normalize_and_validate(value)) is None:
            raise ValueError(
                f"Invalid ISO 639-1 code: '{value}' is not a well-formed or "
                "officially registered ISO 639-1 code.",
            )

        return super().__new__(cls, clean_value)

    @classmethod
    def _normalize_and_validate(cls, value: str) -> str | None:
        """Normalizes and validates a string as an ISO 639-1 code.

        This is the single source of truth for validation logic, used by both
        `__new__` and `is_valid`.

        Args:
            value: The string to validate.

        Returns:
            The cleaned, lowercased code if valid, otherwise None.
        """
        stripped_value = value.strip()
        if (
            len(stripped_value) != cls._CODE_LENGTH
            or not stripped_value.isalpha()
            or not stripped_value.isascii()
        ):
            return None

        clean_value = stripped_value.lower()
        return clean_value if clean_value in cls._VALID_CODES else None

    @classmethod
    def is_valid(cls, value: object) -> bool:
        """Checks if a value is a valid ISO 639-1 code without raising exceptions.

        This method performs the same validation as the constructor but returns
        a boolean, making it suitable for cheap validation checks where
        exception handling is not desired.

        Args:
            value: The value to validate.

        Returns:
            True if the value is a valid ISO 639-1 code, False otherwise.
        """
        if not isinstance(value, str):
            return False
        return cls._normalize_and_validate(value) is not None

    @classmethod
    def valid_codes(cls) -> frozenset[str]:
        """Returns the set of all valid ISO 639-1 codes.

        Returns:
            A frozenset of all valid two-letter ISO 639-1 language codes.
        """
        return cls._VALID_CODES
