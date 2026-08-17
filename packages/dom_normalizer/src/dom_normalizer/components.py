"""Component Loader for the DOM Normalizer.

This module's sole purpose is to import all normalizer processor modules.
This ensures that their `@register_processor_factory` decorators are executed,
populating the central component registry when the application or test suite starts.

This approach avoids circular dependencies and keeps the registration process
clean and centralized.
"""

from . import (
    accessibility_normalizer,  # pyright: ignore[reportUnusedImport] # noqa: F401
    blockquote_processor,  # pyright: ignore[reportUnusedImport] # noqa: F401
    emphasis_normalizer,  # pyright: ignore[reportUnusedImport] # noqa: F401
    floating_element_processor,  # pyright: ignore[reportUnusedImport] # noqa: F401
    footnotes,  # pyright: ignore[reportUnusedImport] # noqa: F401
    heading_normalizer,  # pyright: ignore[reportUnusedImport] # noqa: F401
    language_tagger,  # pyright: ignore[reportUnusedImport] # noqa: F401
    lists,  # pyright: ignore[reportUnusedImport] # noqa: F401
    math_processor,  # pyright: ignore[reportUnusedImport] # noqa: F401
    navigation_purger,  # pyright: ignore[reportUnusedImport] # noqa: F401
    poetry,  # pyright: ignore[reportUnusedImport] # noqa: F401
    table_normalizer,  # pyright: ignore[reportUnusedImport] # noqa: F401
)
