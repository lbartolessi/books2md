"""A multi-layered configuration loading engine for the DOM normalizer.

This module implements a sophisticated, layered approach to configuration
management, providing both global defaults and per-book overrides. This ensures
maximum flexibility for processing large libraries with diverse needs.
"""

import logging
import os
from pathlib import Path

import yaml

from .config import EngineConfiguration

log = logging.getLogger(__name__)


def load_global_config() -> EngineConfiguration:
    """Loads the global base configuration from defaults, .env, and an optional global YAML.

    This function establishes the immutable base configuration for a pipeline run.
    The loading follows a strict precedence order:
    1.  Default values defined in the `EngineConfiguration` model.
    2.  Values from a `.env` file in the project root.
    3.  System environment variables (e.g., `export DOM_NORMALIZER_...`).
    4.  Values from a global YAML file, whose path is specified by the
        `DOM_NORMALIZER_YAML_PATH` environment variable.

    Returns:
        EngineConfiguration: An immutable instance of the global configuration.
    """
    # Steps 1-3: Pydantic-settings automatically handles defaults, .env, and env vars.
    try:
        base_config = EngineConfiguration()
    except Exception:
        log.critical(
            "Failed to initialize base EngineConfiguration. Check .env and environment variables.",
            exc_info=True,
        )
        raise

    # Step 4: Apply optional global YAML override.
    global_yaml_path_str = os.getenv("DOM_NORMALIZER_YAML_PATH")
    if not global_yaml_path_str:
        return base_config

    global_yaml_path = Path(global_yaml_path_str)
    if not global_yaml_path.is_file():
        log.warning(
            "Global config YAML specified in DOM_NORMALIZER_YAML_PATH not found at: %s",
            global_yaml_path,
        )
        return base_config

    log.info("Applying global configuration overrides from: %s", global_yaml_path)
    try:
        with open(global_yaml_path, "r", encoding="utf-8") as f:
            yaml_overrides = yaml.safe_load(f) or {}

        # Create a new configuration instance by applying the overrides.
        # Pydantic's `model_copy` with `update` is the canonical way to do this.
        global_config = base_config.model_copy(update=yaml_overrides)
        return global_config

    except (yaml.YAMLError, IOError) as e:
        log.error(
            "Failed to load or parse global YAML config at %s. Error: %s",
            global_yaml_path,
            e,
        )
        return base_config


def get_book_specific_config(
    global_config: EngineConfiguration,
    book_directory: Path,
) -> EngineConfiguration:
    """Creates a book-specific configuration by applying local overrides.

    This function takes the immutable global configuration, creates a deep copy,
    and then overwrites its values with any settings found in a
    `DOM_NORMALIZER.yaml` file located in the specified book's directory.

    Args:
        global_config: The immutable global configuration object.
        book_directory: The path to the directory containing the book's files.

    Returns:
        EngineConfiguration: A new configuration instance tailored for the specific book.
    """
    # Start with a deep copy of the global config to ensure isolation.
    book_config = global_config.model_copy(deep=True)

    local_yaml_path = book_directory / "DOM_NORMALIZER.yaml"

    if not local_yaml_path.is_file():
        return book_config  # No local overrides, return the cloned global config.

    log.info("Applying book-specific overrides from: %s", local_yaml_path)
    try:
        with open(local_yaml_path, "r", encoding="utf-8") as f:
            local_overrides = yaml.safe_load(f) or {}

        # Apply local overrides to the cloned configuration.
        book_config = book_config.model_copy(update=local_overrides)
        return book_config

    except (yaml.YAMLError, IOError) as e:
        log.error(
            "Failed to load or parse book-specific YAML config at %s. Using global config. Error: %s",
            local_yaml_path,
            e,
        )
        return global_config.model_copy(deep=True)  # Return a fresh clone


if __name__ == "__main__":
    # Example of how to use the layered configuration loader in an application.
    # This would typically be in your main application entry point.

    # 1. Load the immutable global configuration once at startup.
    GLOBAL_CONFIG = load_global_config()

    def process_book(book_path_str: str) -> None:
        """Simulates processing a single book with its specific configuration."""
        book_dir = Path(book_path_str)
        print(f"\n--- Processing book in: {book_dir} ---")

        # 2. For each book, get its specific, isolated configuration.
        book_config = get_book_specific_config(GLOBAL_CONFIG, book_dir)

        print(f"Final 'max_heading_length' for this book: {book_config.max_heading_length}")
        print(f"Final 'min_viable_list_items' for this book: {book_config.min_viable_list_items}")

    # --- DEMO ---
    # process_book("path/to/book1")
    # process_book("path/to/book2")