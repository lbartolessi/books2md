"""Defines the abstract contract for book container ingestion.

This module provides the `BaseBookLoader` abstract base class, which establishes
a uniform interface for handling various digital book formats (e.g., EPUB, FB2).
By enforcing a consistent API for opening, parsing, and accessing book data, it
decouples the main normalization pipeline from the structural specifics of any
given format.

It also defines the `BookLoadError` exception, which is critical for the
project's fault-isolation principle, ensuring that a single corrupted book
cannot halt a larger batch processing job.
"""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup


class BookLoadError(Exception):
    """Custom exception for failures in book loading, decompression, or parsing.

    This exception is raised when a book source container is corrupted, cannot
    be opened, or fails parsing. It is designed to be caught at the orchestrator
    boundary, upholding the project's fault-isolation principle: a single
    corrupted book must never crash an entire batch run.
    """


@dataclass
class BookManifest:
    """Serves as a structured container for essential book metadata.

    This dataclass provides a type-safe, explicit contract for the metadata
    returned by book loaders.
    """

    title: str | None
    primary_language: str | None
    spine_order: list[str]


class BaseBookLoader(ABC):
    """A format-agnostic abstract contract for book container ingestion.

    This abstract base class defines a uniform interface for loading and
    accessing book data. Concrete subclasses must implement the abstract methods
    to handle the specifics of a given format (e.g., EPUB's multi-file manifest
    versus FB2's single-file structure). This ensures that the rest of the
    system can process any book format through a consistent API.

    The class supports the context manager protocol, ensuring that resources
    are properly released via the `close` method upon exiting a `with` block.
    """

    @abstractmethod
    def open(self, source_path: Path) -> None:
        """Opens and prepares a book container for processing.

        Implementations should handle decompression (if applicable) and parse the
        container's top-level structure, such as a manifest or spine index, to
        make the book's contents accessible.

        Args:
            source_path: The file system path to the book container.

        Raises:
            BookLoadError: If the source cannot be opened, is corrupted, or fails
                initial parsing. Implementations must not raise raw exceptions.

        Mutations:
            Initializes the internal state of the loader instance, making it
            ready to serve content via other methods.
        """

    @abstractmethod
    def get_soup(self, file_key: str) -> BeautifulSoup:
        """Returns the parsed BeautifulSoup tree for a single content file.

        Args:
            file_key: A unique string identifier for a content file within the
                book container (e.g., a path from an EPUB manifest).

        Returns:
            A `BeautifulSoup` object representing the parsed content of the file.

        Rules & Logic:
            - Implementations MUST cache parsed results internally. Repeated calls
              with the same `file_key` must return the cached object and not
              re-parse the source file.
        """

    @abstractmethod
    def get_soups_dict(self) -> dict[str, BeautifulSoup]:
        """Returns all content files as a dictionary of BeautifulSoup objects.

        This method provides bulk access to all parsed content files in the book,
        keyed by their unique file identifiers.

        Returns:
            A dictionary mapping each `file_key` to its corresponding parsed
            `BeautifulSoup` object.

        Rules & Logic:
            - This method is intended for memory-intensive, cross-file analysis
              (e.g., forensic pattern analysis) and should be used with caution.
            - For sequential processing, `iterate_soups()` is preferred to avoid
              loading the entire book into memory at once.
        """

    @abstractmethod
    def get_manifest_info(self) -> BookManifest:
        """Returns essential book-level metadata.

        Returns:
            A `BookManifest` object containing structured book metadata.
        """

    @abstractmethod
    def get_native_notes_location(self) -> str | None:
        """Returns the file key for a format's native, schema-defined notes section.

        Some formats, like FB2, have a guaranteed location for footnotes within
        their schema. Others, like EPUB, do not. This method identifies if such
        a location exists.

        Returns:
            A string `file_key` if a native notes location is guaranteed by the
            format's specification (e.g., 'body:notes' for FB2). Returns `None`
            if no such guarantee exists (e.g., for EPUB).

        Rules & Logic:
            - A non-None return value is a promise that the reference is
              trustworthy by construction. The orchestrator uses this to activate
              specialized footnote processing.
        """

    def iterate_soups(self) -> Iterator[tuple[str, BeautifulSoup]]:
        """Yields (file_key, soup) pairs in the book's reading order.

        This convenience method provides an efficient way to process a book's
        content files sequentially without loading the entire book into memory.

        Yields:
            An iterator of `(str, BeautifulSoup)` tuples, where the first
            element is the file key and the second is the parsed soup object.

        Mutations:
            None.

        Rules & Logic:
            - The iteration order is determined by the `spine_order` list
              retrieved from `get_manifest_info()`.
            - For each file key in the spine, it calls `get_soup()` to retrieve
              the content.
        """
        for file_key in self.get_manifest_info().spine_order:
            yield file_key, self.get_soup(file_key)

    @abstractmethod
    def close(self) -> None:
        """Releases any held resources, such as open file handles.

        This method is a no-op by default. Subclasses that manage system
        resources (like open zip archives) MUST override this method to ensure
        proper cleanup. It is called automatically when the loader is used as a
        context manager.

        Mutations:
            Releases file handles or other system resources held by the instance.
        """

    def __enter__(self) -> "BaseBookLoader":
        """Enters the runtime context for the `with` statement."""
        return self

    def __exit__(self, *exc_info) -> None:
        """Exits the runtime context, ensuring resources are released.

        Args:
            *exc_info: Standard context manager exit arguments (type, value, traceback).

        Mutations:
            Calls `self.close()` to guarantee resource cleanup.
        """
        self.close()
