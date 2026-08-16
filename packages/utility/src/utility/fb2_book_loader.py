"""A concrete book loader for the FictionBook (FB2) container format.

This module provides `Fb2BookLoader`, an implementation of `BaseBookLoader`
that handles the single-XML structure of the FB2 format. It adapts this
monolithic structure to the multi-file contract required by the normalization
pipeline by treating each `<body>` tag within the FB2 file as a "virtual file."

This virtualization allows downstream processors, like `ForensicPatternAnalyzer`,
to consume a consistent `dict[str, BeautifulSoup]` interface regardless of
whether the source format is a multi-file EPUB or a single-file FB2.
"""

import zipfile
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from dom_normalizer.utility.base_book_loader import (
    BaseBookLoader,
    BookLoadError,
    BookManifest,
)


class Fb2BookLoader(BaseBookLoader):
    """Parses FictionBook's single-XML structure into virtual documents.

    This class adapts the monolithic FB2 format to the multi-file contract of
    `BaseBookLoader`. It parses the entire FB2 file into a single master soup
    and then treats each `<body>` element as a separate "virtual file." This
    ensures that downstream consumers receive a `dict[str, BeautifulSoup]`
    identical in shape to that produced by `EpubBookLoader`.

    Attributes:
        _soup (Optional[BeautifulSoup]): The master `BeautifulSoup` object
            containing the entire parsed FB2 file.
        _body_keys (dict[str, Any]): A dictionary mapping virtual file keys
            (e.g., 'body:main', 'body:notes') to their corresponding `<body>`
            `Tag` objects from the master soup.

    Rules & Logic:
        - The `lxml-xml` parser is used for its namespace-aware handling, which
          is important for attributes like `xlink:href`.
    """

    VIRTUAL_KEY_MAIN_PREFIX = "body"

    def __init__(self) -> None:
        """Initializes the Fb2BookLoader with an empty state.

        Mutations:
            - Initializes `self._soup` to `None`.
            - Initializes `self._body_keys` to an empty dictionary.
        """
        self._soup: BeautifulSoup | None = None
        self._body_keys: dict[str, Any] = {}  # virtual_key -> <body> Tag

    def open(self, source_path: Path) -> None:
        """Opens an FB2 file, parses it, and identifies all virtual documents.

        This method reads a potentially zipped FB2 file, parses the entire XML
        content, and then iterates through all `<body>` tags to create a mapping
        of virtual file keys to the tag objects.

        Args:
            source_path: The file system path to the FB2 file, which may be
                a raw `.fb2` or a zipped `.fb2.zip`.

        Raises:
            BookLoadError: If the file cannot be opened, read, or parsed.

        Mutations:
            - Assigns the parsed `BeautifulSoup` object to `self._soup`.
            - Populates `self._body_keys` with mappings from virtual keys to
              `<body>` tags.

        Rules & Logic:
            - Virtual keys are generated as `body:<name>` if the `<body>` tag has
              a `name` attribute; otherwise, they are `body:<index>`.
        """
        try:
            raw_bytes = self._read_possibly_zipped(source_path)
            self._soup = BeautifulSoup(raw_bytes, "lxml-xml")
        except Exception as e:
            raise BookLoadError(f"Failed to open FB2 container: {e}") from e

        bodies = self._soup.find_all("body")
        for index, body in enumerate(bodies):
            name = body.get("name")
            virtual_key = (
                f"{self.VIRTUAL_KEY_MAIN_PREFIX}:{name}"
                if name
                else f"{self.VIRTUAL_KEY_MAIN_PREFIX}:{index}"
            )
            self._body_keys[virtual_key] = body

    def get_soup(self, file_key: str) -> BeautifulSoup:
        """Returns a minimal BeautifulSoup object for a single virtual document.

        To maintain interface uniformity with multi-file formats, this method
        takes a virtual `file_key`, retrieves the corresponding `<body>` tag,
        and wraps its string representation in a new, minimal `BeautifulSoup`
        object.

        Args:
            file_key: The virtual key identifying the desired `<body>` section
                (e.g., 'body:main').

        Returns:
            A new `BeautifulSoup` object containing only the markup of the
            requested `<body>` tag.

        Raises:
            KeyError: If the `file_key` does not exist in `self._body_keys`.
        """
        return BeautifulSoup(str(self._body_keys[file_key]), "lxml-xml")

    def get_soups_dict(self) -> dict[str, BeautifulSoup]:
        """Returns all virtual documents as a dictionary of BeautifulSoup objects.

        This method iterates through all identified virtual body keys and calls
        `get_soup()` for each one to construct the complete dictionary.

        Returns:
            A dictionary mapping each virtual `file_key` to its corresponding
            newly created `BeautifulSoup` object.
        """
        return {key: self.get_soup(key) for key in self._body_keys}

    def get_manifest_info(self) -> BookManifest:
        """Returns essential book-level metadata.

        This implementation provides a spine order based on the discovered
        `<body>` tags, excluding the dedicated notes section. Title and language
        parsing is noted as a future task.

        Returns:
            A `BookManifest` object containing the book's metadata.

        Rules & Logic:
            - 'title': Returns `None` as parsing from `<description>` is pending.
            - 'primary_language': Returns `None` as parsing is pending.
            - 'spine_order': A list of all virtual body keys, excluding any key
              that ends with the suffix `:notes`.
        """
        return BookManifest(
            title=None,
            primary_language=None,
            spine_order=[k for k in self._body_keys if not k.endswith(":notes")],
        )

    def get_native_notes_location(self) -> str | None:
        """Returns the file key for the format's native notes section.

        The FB2 specification provides a standard mechanism for a dedicated
        notes section, typically `<body>` with `name="notes"`. This method
        checks for its existence.

        Returns:
            The string 'body:notes' if a `<body>` tag with `name="notes"` was
            found during parsing. Otherwise, returns `None`.
        """
        notes_key = f"{self.VIRTUAL_KEY_MAIN_PREFIX}:notes"
        return notes_key if notes_key in self._body_keys else None

    def close(self) -> None:
        """Resets the loader's internal state.

        This method resets the internal state to prevent misuse of a closed
        loader. It is called automatically when the loader is used as a
        context manager.

        Mutations:
            - Resets `self._soup` to `None`.
            - Resets `self._body_keys` to an empty dictionary.
        """
        self._soup = None
        self._body_keys = {}

    def _read_possibly_zipped(self, source_path: Path) -> bytes:
        """Reads an FB2 file, handling both raw XML and zipped archives.

        FB2 files are distributed either as raw `.fb2` XML files or as `.fb2.zip`
        archives containing a single `.fb2` file. This method detects the format
        and returns the raw bytes of the XML content.

        Args:
            source_path: The path to the `.fb2` or `.fb2.zip` file.

        Returns:
            The raw byte content of the enclosed or direct `.fb2` file.

        Raises:
            BookLoadError: If a zipped archive is provided but it is malformed,
                or if it does not contain exactly one `.fb2` file.
        """
        if source_path.suffix.lower() == ".zip":
            with zipfile.ZipFile(source_path, "r") as zf:
                fb2_files = [
                    name for name in zf.namelist() if name.lower().endswith(".fb2")
                ]
                if len(fb2_files) != 1:
                    raise BookLoadError(
                        f"FB2 zip archive must contain exactly one .fb2 file, but {len(fb2_files)} were found in {source_path}",
                    )
                return zf.read(fb2_files[0])
        return source_path.read_bytes()
