# Architecture and Dependency Index: Base Modules

This document summarizes the location and purpose of the essential classes and functions of the base infrastructure for their correct use and import in other pipeline modules.

## 1. Module: `core.py`

Provides the main infrastructure, execution contracts, and the molecular design matching engine. Its design ensures the absence of concurrency risks by not using shared mutable states.

### Main Classes

* **`PipelineStatus` (Enum):** Canonical surface for tracking the state of metadata throughout the pipeline (values: `SUCCESS`, `IDLE`, `ERROR`).

* **`ISOLanguageCode`:** Immutable Value Object that guarantees deterministic validation of ISO 639-1 language codes (e.g., 'es', 'en').

* **`EngineConfiguration`:** Immutable dataclass that stores the global execution parameters of the engine, initializable from environment variables via `from_env()`.

* **`BookStyleContext`:** Thread-isolated context container that stores and evaluates the structural design profile of a book.

* *Node evaluation methods:* `is_floating_element`, `is_blockquote_element`, `is_italic_element`, `is_bold_element`.

* *Protection mechanisms:* `is_inside_code_block`, `is_inside_literal_code_tag`.

* *Integrated mutators:* `normalize_inline_floats`, `normalize_inline_indents`.

### Structural Analysis and Mutation Functions

* **`tokenize_spacer_line`:** Cleans and tokenizes rows of tabular text separated by spaces or tabs.

* **`is_page_marker_noise`:** Evaluates if a text is a non-semantic pagination artifact (e.g., "Pág. 12").

* **`safe_convert_div_grid_to_table`:** Mutator that safely converts a grid-like `<div>` container into a semantic `<table>` tag.

* **`is_ignorable_node`:** Evaluates if a structural node is disposable noise (whitespace, line breaks, page markers).

### Normalizer and Metadata Utilities

* **`validate_list_viability`:** Validates that a candidate list has at least 2 structural items.

* **`generate_pipeline_metadata`:** Constructs the standard metadata dictionary required by the specification, using `PipelineStatus`.

* **`safe_mutation_boundary`:** Context manager (`@contextmanager`) that isolates the mutations of an individual node to prevent errors from aborting the pipeline execution.

### Helper Functions

* **`get_utc_timestamp`:** Generates and returns a UTC timestamp in canonical ISO 8601 format (`%Y-%m-%dT%H:%M:%SZ`).

* **`coerce_class_list`:** Safely normalizes the `class` attribute of an HTML node (received from BeautifulSoup) into a mutable list of text strings.

---

## 2. Module: `utils.py` (Implicitly referenced from `dom_normalizer.utils`)

Provides generic helper functions and telemetry utilities without circular dependencies.

### Orchestration Classes

* **`TelemetryLedger`:** Optional dataclass used by orchestrators to aggregate telemetry data across batch executions.

* *Methods:* `record_document`, `record_error`, `to_dict`.

* *Architectural rule:* No individual processing module requires or references this class.
