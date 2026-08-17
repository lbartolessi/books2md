"""A multi-strategy engine for footnote detection, isolation, and normalization."""

# Import the processor module to ensure its factory is registered.
from . import footnote_processor  # pyright: ignore[reportUnusedImport] # noqa: F401