# TECHNICAL SPECIFICATION: `table_normalizer` PACKAGE (Version 1.5 - FORENSIC TABULAR RECOVERY)

## 1. Purpose and Scope

The `table_normalizer` module is a forensic reconstruction and relational consolidation engine (Stage 2 - Document Structure Layer). Its exclusive objective is to intercept visual scaffolding composed of layout-oriented `<div>` grids, preformatted text blocks, or native `<table>` structures artificially fragmented due to physical pagination, mutating them into semantic, continuous, and perfectly unified XHTML tables.

### Stage 2 Pipeline Order Contract

Within the Document Structure Layer execution pool, operations must respect an immutable execution sequence to prevent greedy token-matching conflicts:

$$\text{heading\_normalizer} \longrightarrow \mathbf{\text{table\_normalizer}} \longrightarrow \text{list\_normalizer} \longrightarrow \text{blockquote\_processor}$$

`table_normalizer` must run strictly **before** `list_normalizer` to prevent multi-column preformatted numbers from being misidentified as numeric ordered lists, ensuring data matrix alignment remains unbroken.

---

## 2. The "Bestiary" of False Tables (Identified Patterns)

### CASE A: The Container Grid (`Div-Based Grid`)

The exporter mimics tabular visual geometry using `<div>` trees with explicit layout classes matching the layout regular expression:

```python
ROW_CELL_GRID_RX = re.compile(r'\b(?:row|cell|col|grid|table)\b', re.IGNORECASE)

```

> **Boundary Safeguard Note:** The explicit use of word boundaries (`\b`) is required to prevent catastrophic false-positive matches on non-structural substrings (e.g., `browser-toolbar`, `cellular-note`, `tablet-icon`, or `collapse-panel`).
>
>

### CASE B: The Page-Break Fragmented Table (`Split Table`)

Legitimate `<table>` structures that have been physically split by an intrusive pagination element (an orphaned page number, a repeated section header, or a line break tag).

### CASE C: The False Preformatted Text Table (`Spacer Table`)

Tabular data simulated within normal paragraphs or inside a `<pre>` block by filling intermediate spaces with tabs or sequences of whitespaces (`\s{2,}`).

---

## 3. Normalization Algorithm Architecture (BeautifulSoup4)

### 3.1. Guard Clause and Immunity Protocol

The module invokes `self._context.is_inside_literal_code_tag(node)`. If the node is wrapped inside a literal programming tag (`<code>`), processing is aborted. However, bare `<pre>` blocks **are explicitly allowed to pass through** validation to guarantee that CASE C spacer tables hidden inside preformatted blocks are reachable.

### 3.2. Internal Layer Execution Order

To ensure predictable interactions between normalization layers and allow forensic fusion of text-extracted tables, internal methods must be executed in the following strict sequence:

1. **`_extract_spacer_tables()`**: Must run first to convert preformatted text into initial `<table>` structures before any structural clustering happens.

2. **`_reconstruct_div_grids()`**: Runs second to convert container-based layouts.

3. **`_fuse_fragmented_tables()`**: Must run last to consolidate all generated or existing tables now that they share a uniform `<table>` tag interface.

### 3.3. Layer 1: Topological Reconstruction (Div Substitution)

When the engine detects the **CASE A** pattern via `ROW_CELL_GRID_RX` or when $\ge 2$ contiguous container rows each contain $\ge 2$ child nodes sharing identical class profiles:

1. Mutates the parent container name to `<table>` and **appends** the `table-block` class to its existing class list, preserving pre-existing layout classes (e.g., `class="grid table-block"`).

2. **XHTML Compliance Invariant:** Inserts a mandatory `<tbody>` structural container directly inside the mutated `<table>` node. All rows must be appended as children of this `<tbody>`.
3. Mutates the intermediate row containers to `<tr>`.
4. Mutates the cell containers to `<th>` if they belong to the first row of the block, or `<td>` for all subsequent rows.

5. **Attribute Cleansing Discipline:** Strips layout-centric inline `style` variables from the tags. **It is strictly forbidden** to wipe or empty the entire attribute dictionary (`node.attrs = {}`), ensuring that non-presentational metadata and original semantic classes remain completely intact.

### 3.4. Layer 3: Preformatted Space-Separated Table Extraction (Case C)

When a `<pre>` or `<p>` node contains text lines matching the tabular spacer signature (lines containing three or more data tokens separated by clusters of $\ge 2$ consecutive spaces or raw tabs):

1. **Heuristic Threshold:** The engine activates if the node contains **at least one** line matching the tabular signature with $\ge 3$ columns.

2. The engine splits the node's internal text into distinct row strings using standard line-break characters.

3. **DOM Mutation & Adjacency Invariant:** The parent node is replaced **directly** by a structural `<table>` element carrying the `["table-block"]` class. **It is strictly forbidden** to wrap this new table inside an intermediate layout `<div>` (such as `table-block-spacer`), ensuring the element remains a direct sibling to adjacent nodes to allow downstream fusion.
4. **Semantic Header Assignment:** The first extracted text line is mapped to a `<tr>` containing exclusively `<th>` cells. All subsequent lines are mapped to `<tr>` elements containing `<td>` cells. Raw presentational spacing text is completely purged.

### 3.5. Layer 2: Relational Fusion by Column Heuristics (`Table Fusion`)

To solve **CASE B** and eliminate false-positive fusions between independent consecutive tables:

```text
[Table A Detected] ──► Calculate cells per row (N)
                             │
                             ▼
                Is the next sibling noise? (page-break classes, loose numbers, <br/>)
                             ├── YES ──► Store noise temporarily and check the next sibling.
                             ▼
               [Is the next node a direct sibling `<table>`?]
                             ├── YES ──► Verify Table B lacks structural headers (<th>)
                             │               │
                             │               ▼
                             │         Calculate cells per row (M)
                             │               │
                             │               ▼
                             │         Is N == M?
                             │               ├── YES ──► [FUSION ACTIVATED]
                             │               └── NO ──► Abort (Different tables).
                             └── NO ──► Abort fusion.

```

* **Sibling Contiguity Guard:** The fusion logic operates exclusively on direct, un-wrapped sibling `<table>` nodes. If fusion criteria are met, all `<tr>` elements from Table B are appended directly into Table A's `<tbody>`, and both the temporary noise elements and the emptied Table B container are completely decomposed from the DOM.

---

## 4. Thread-Safety & OOP Design Constraints

* **Pipeline Return Contract:** The `process` method **must** return a tuple of two elements: `(BeautifulSoup, Dict[str, Any])`.

* **BeautifulSoup4 Multi-Valued Attribute Rule:** When writing or mutating a node's class attribute, values must always be assigned as a native Python list of strings (e.g., `node['class'].append('table-block')`). Joining them into a space-separated string expression is strictly forbidden.

### CRITICAL RECONSTRUCTION GUARDRAILS & PROHIBITIONS

1. PROHIBITED: Leading Whitespace Splitting in Spacer Tables
   * You MUST NOT run whitespace splitting regexes directly on un-trimmed raw lines.
   * Every line extracted from a `<pre>` or `<p>` block MUST be independently stripped (`line.strip()`) BEFORE applying the columns splitting regex.
   * Any empty string tokens resulting from the split MUST be explicitly filtered out before DOM element generation to prevent ghost columns/cells.

2. MANDATORY: Robust Page-Marker Noise Detection
   * The `_is_noise_element` logic MUST NOT rely solely on `.isdigit()` to identify page numbers or headers/footers between tables.
   * You MUST implement a case-insensitive regular expression capable of identifying typical automated page number formats (e.g., matching "Page X", "Pág. X", "Página X", or just raw numbers "X").
   * Recommended regex pattern: `^([pP]ág(ina)?|[pP]age)?\s*\d+$`

## ARCHITECTURAL DELEGATION CONTRACT (CRITICAL)

To prevent regression errors, edge-case failures, and duplicated parsing logic, this module MUST NOT implement local string-tokenization heuristics or custom regular expressions for layout noise detection. It is MANDATORY to delegate these operations to the centralized engine utilities.

### 1. Spacer Table Line Parsing

* **Context:** Inside the `_extract_spacer_tables` pipeline stage, when converting pre-formatted lines into distinct column tokens.
* **Mandatory Action:** You MUST import and invoke `tokenize_spacer_line(line: str) -> list[str]` from `dom_normalizer.utils.core`.
* **Prohibited Implementation:** DO NOT declare local expressions like `SPACER_TABLE_LINE_RX`. DO NOT perform raw line splits directly within this module. The responsibility of stripping whitespace and filtering empty ghost elements belongs exclusively to the core module.

### 2. Pagination Noise Evaluation

* **Context:** Inside the `_is_noise_element` method, when deciding if an intermediate node is ignorable layout noise (e.g., page markers) between two tables.
* **Mandatory Action:** Extract the node's text via `node.get_text(strip=True)` and evaluate it strictly using `is_page_marker_noise(text: str) -> bool` from `dom_normalizer.core`. If it returns `True`, the node is identified as noise.
* **Prohibited Implementation:** DO NOT use raw `.isdigit()` checks to discover page numbers. DO NOT implement custom local regex patterns to intercept string variants like "Page X" or "Pág. X".

### 3. Class List Coercion and Element Mutation

* **Context:** When reading, normalizing, or appending classes to a DOM element during structural conversion (e.g., transforming a container into a `<table>` or a child into a `<tr>`/`<td>`).

* **Mandatory Action:** You MUST pass only the raw value of the class attribute (`node.get("class")`) as a single positional argument to `coerce_class_list()`. This function returns a standard mutable `list[str]`. To append new classes (like `"table-block"`), you must append the token to that returned list and then reassign it to the node's `["class"]` attribute.
* **Prohibited Implementation:**
  * DO NOT pass the BeautifulSoup `Tag` object directly as an argument to `coerce_class_list()`.
  * DO NOT pass a second argument or target class string to `coerce_class_list()`. It strictly accepts exactly one positional argument representing the class collection.

### 4. Content-Driven Retention and Purging (Ockham's Razor Rule)

* **Textual Presence Rule:** The conversion of explicit layout containers (`div` with grid/table classes) into `<table>` structural elements is binary and driven solely by content, completely ignoring dimensional or coordinate thresholds ($1 \times 1$ grids are valid).
* **Action (Has Text):** If the container or any of its layout children contains text nodes (non-whitespace structural content), the entire block MUST be reconstructed into a valid `<table>` infrastructure (with its corresponding `<tbody>`, `<tr>`, and `<th>`/`<td>` mappings) to preserve layout hierarchy for the downstream formatted markdown.
* **Action (Empty/No Text):** If the container and its internal sub-elements contain zero textual data (empty nodes or purely structural whitespace), it is classified as presentation noise. The normalizer MUST purge the entire node tree from the DOM to eliminate layout clutter before the RAG extraction phase.### Required Imports Checklist

Every automated refactor or reconstruction of `table_normalizer.py` MUST explicitly feature the following contract allocation:

```python
from dom_normalizer.core import BookStyleContext, is_page_marker_noise,
    tokenize_spacer_line
from dom_normalizer.core import coerce_class_list

### 4.1. Structural Boundaries and Immunity Invariants (Anti-Hallucination Guard)
* **Immunity Enforcement:** Every processing layer (Spacer Tables, Div-grids, and Fusion) MUST independently evaluate and respect code block immunity. If `is_inside_literal_code_tag(node)` returns `True`, the normalizer MUST immediately skip the node and all its children.
* **Strict Boundary Rule:** The scope of conversion for Case A MUST be strictly isolated to the specific layout container matching the heuristics. Under NO circumstances layout normalizers are allowed to mutate or replace ancestor structural tags (such as `<body>`, `<main>`, or root wrappers). 
* **Whitespace & Structural Noise Definition:** Any structural tag (e.g., `<br/>`, or empty layout divs like `<div class="page-break"></div>`) that returns zero non-whitespace characters via text extraction MUST be explicitly treated as ignorable noise during the Case B (Table Fusion) adjacency analysis.

### 5. Mandatory Implementation Requirements & Shared Utilities
To prevent DOM tree corruption and recursive tag-nesting hallucinations, the implementation MUST strictly delegate atomic structural modifications and adjacency evaluations to the verified utility functions in `dom_normalizer.core`:

1. **Case A (Div Grids) Mutation Rule:** The normalizer MUST NOT perform manual tag name rewrites on loop variables. It MUST locate the valid layout container and immediately delegate the entire structural mutation to `safe_convert_div_grid_to_table(container, soup)`.
2. **Case B (Table Fusion) Noise Rule:** When scanning siblings between two tables to detect if they are adjacent, the loop MUST evaluate every intermediate element using `is_ignorable_table_noise(node)`. If it returns `True`, the node is skipped/collected as noise; if `False`, the fusion pipeline for that node pair MUST break immediately.
3. **BS4 Safeguard Invariant:** Adjacency and noise analysis functions MUST evaluate types strictly using explicit class check primitives (`isinstance(node, str)`) rather than dynamic attribute sniffing (`hasattr`), to prevent BeautifulSoup's virtual child resolution overrides from returning false positives on missing methods.