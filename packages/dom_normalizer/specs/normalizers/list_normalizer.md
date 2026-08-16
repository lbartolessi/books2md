# SPECIFICATION: `list_normalizer` PACKAGE (Version 1.4 - DETERMINISTIC STRUCTURAL LIST RECOVERY)

## 1. Purpose and Scope

The `list_normalizer` module is a reconstruction and consolidation engine (Stage 2 - Document Structure Layer). Its function is twofold: 1) to intercept sequences of common paragraphs (`<p>`) that visually simulate lists and mutate them into semantic list structures (`<ul>`, `<ol>`), and 2) to fuse fragmented lists of the same type that are separated by non-semantic noise.

### Stage 2 Pipeline Order Contract

Within the Document Structure Layer execution pool, operations follow this sequence:

$$\text{heading\_normalizer} \longrightarrow \text{table\_normalizer} \longrightarrow \mathbf{\text{list\_normalizer}} \longrightarrow \text{blockquote\_processor}$$

`list_normalizer` processes text sequences after table extractions have occurred, ensuring that complex space-separated tabular data blocks do not suffer item fragmentation under prefix checking rules.

---

## 2. The "Bestiary" of False Lists (Identified Patterns)

### **RECONSTRUCTION PATTERNS**

#### CASE A: Explicit Textual Prefix (Hanging Bullet)

Contiguous sibling `<p>` nodes whose plain text begins with a rigid bullet or alphanumeric counter pattern.

#### CASE B: Vendor Class Signature (InDesign / Word / Calibre)

`<p>` nodes that do not show an explicit bullet character but whose classes betray their sequential linear nature.

#### CASE C: Fragmented Multiline Items

A legitimate list item split into two or more physical paragraphs. The first features the prefix or list class; subsequent paragraphs are regular blocks acting as structural continuations of the same statement.

---

## 3. Normalization Algorithm Architecture (BeautifulSoup4)

### 3.1. Guard Clause (Code Shield)

Before analyzing any node, `self._context.is_inside_code_block(node)` is invoked. If the sequence is inside a `<code>` or `<pre>` block, it is completely bypassed to safeguard code syntax examples.

### 3.2. Prefix Capture Regular Expressions

The engine compiles analytical expressions as immutable class-level constants using `Final[re.Pattern]`:

* **`UNORDERED_PREFIX_RX`**: `re.compile(r'^\s*([\-\*\u2022\u25b6\u2013])\s+')`

* **`ORDERED_PREFIX_RX`**: `re.compile(r'^\s*(?:(\(?\d+[\.\)])|(\(?[a-zA-Z][\.\)])|(\(?[ivxIVX]+[\.\)]))\s*')`
  
### 3.3. CASE B: Vendor Class Signature Heuristic

To handle documents where list structure is defined by CSS classes instead of textual prefixes, the engine must use a set of known vendor-specific class name patterns.

* **`LIST_CLASS_KEYWORDS`**: A set containing lowercase substrings that identify list-related paragraphs (e.g., `"list"`, `"item"`, `"bullet"`, `"calibre"`, `"idgenparagraphstyle"`).
* **Detection Logic:** A paragraph is considered a list item under this heuristic if it passes the following sequence:
    1. The `class` attribute of the `<p>` tag is retrieved.
    2. **MANDATORY DELEGATION:** This attribute is passed to the `coerce_class_list` core function to obtain a consistent list of class strings.
    3. Each class string is normalized (converted to lowercase, underscores removed).
    4. The engine checks if any of the normalized class strings contain one of the keywords from `LIST_CLASS_KEYWORDS`.

### 3.4. CASE C: Fragmented Multiline Items (Continuation Logic)

A "continuation paragraph" is defined as a `<p>` tag that does **not** match either the textual prefix heuristic (Case A) or the vendor class heuristic (Case B), but which is an immediate sibling following a paragraph that **was** identified as a list item.

### 3.3. Topological Grouping FSM Logic with Dynamic Lookahead Safeguards

1. **Dynamic Lookahead Verification:** When a paragraph $P_n$ matches a prefix expression, the engine scans its contiguous downstream siblings dynamically. It continues to consume and bypass consecutive paragraphs that satisfy the Case C continuation pattern.
2. **Hard Commit Criteria (The Rollback Guard):** A minimum of **2 distinct structural list items** must be encountered along the dynamic traversal path to validate the block. **Strict Rule:** If the lookahead traversal concludes without identifying at least 2 valid, distinct prefix-marked items, the FSM must trigger an immediate abort. It is strictly forbidden to create a list block or modify the DOM if this count is not met; the sequence must be left entirely unmutated.
3. **Block Opening and DOM Anchoring:** Upon validation (count $\ge$ 2), the FSM instantiates `<div class="list-block">`. The new container must be inserted strictly before the first matched paragraph using `insert_before()` prior to any `.extract()` operations.
4. **Hierarchical Depth Tracking (The Stack Rule):** The FSM must maintain a stack of containers and classify prefixes (`numeric`, `alphabetic`, etc.). If a prefix type changes (e.g., from `numeric` to `alphabetic`), the FSM **must** immediately append a new nested list to the last created `<li>` in the current container and push it to the stack.
5. **Item Consolidation and Structural Integrity:** Each `<li>` created must explicitly encapsulate the content of the source paragraph within a `<p>` tag (e.g., `<li><p>Content</p></li>`) to preserve document block-level semantics. The original prefix must be purged from the text node. The original `<p>` node is only extracted from the DOM after the new `<p>`-wrapped content is safely appended to the `<li>`.

---

## 4. Thread-Safety & OOP Design Constraints

* **Immutable Pattern Caching:** `UNORDERED_PREFIX_RX` and `ORDERED_PREFIX_RX` are compiled as read-only class constants (`Final[re.Pattern]`).

* **Ephemeral FSM State Isolation:** All FSM parameters (active blocks, counter values, multiline context states) must be strictly confined to local variables within the scope of the `process()` execution frame.

* **BeautifulSoup4 Class Mutation Protocol:** Any updates to a node's class property within list normalization utility routines must assign an explicit list of strings (`node['class'] = classes_list`). String serialization (`" ".join(classes)`) is strictly prohibited.

* **Object Architecture Template:**

```python
from typing import Final, Tuple, Dict, Any
import re
from bs4 import BeautifulSoup
from dom_normalizer.core import BookStyleContext

class ListNormalizer:
    UNORDERED_PREFIX_RX: Final[re.Pattern] = re.compile(r'^\s*([\-\*\u2022\u25b6\u2013])\s+')
    ORDERED_PREFIX_RX: Final[re.Pattern] = re.compile(r'^\s*(\(?\d+[\.\)]|\(?[a-zA-Z][\.\)]|\(?[ivxIVX]+[\.\)])\s*')

    def __init__(self, context: BookStyleContext) -> None:
        self._context = context
        self._unordered_recovered: int = 0
        self._ordered_recovered: int = 0
        self._multiline_welded: int = 0
        self._paragraphs_purged: int = 0

    def process(self, soup: BeautifulSoup) -> Tuple[BeautifulSoup, Dict[str, Any]]:
        """Orchestrates sequential conversion of degraded paragraphs to semantic lists."""
        if self._context.is_inside_code_block(soup):
            return soup, {"status": "idle"}
            
        # ALL FSM local state variables are declared strictly inside this local execution frame
        active_list_container = None
        ...

```

---

## 5. Mandato de Integración con `core.py`

The `ListNormalizer` module must delegate state decisions and structural validation to shared utilities. The internal logic must adhere to the following mandates:

### 5.1. MANDATORY DELEGATION: List Viability Validation (Rollback Guard)

* **Requirement:** Before instantiating any list container (`<ol>` or `<ul>`), the `process()` method MUST invoke `self._validate_list_viability(candidates: list[Tag]) -> bool`.
* **Action on Failure:** If validation returns `False`, the process MUST abort immediately for that block. The original `soup` object must be returned without mutation for that block, and the final status should reflect `IDLE` if no other changes were made.

### 5.2. MANDATORY DELEGATION: Metadata and State Contract

* **Requirement:** It is forbidden to manually construct the metadata dictionary or define the `status` using string literals ("success", "idle"). The metadata generation is an internal responsibility of the normalizer.
* **Mandatory Action:** Every return point of `process()` MUST use `self._get_metadata(status: PipelineStatus) -> dict`. This ensures that the `PipelineStatus.SUCCESS` or `PipelineStatus.IDLE` states are consistent with the processing outcome.

### 5.3. Jerarquía (The Stack Rule)

* **Requirement:** Hierarchical depth tracking must not be ad-hoc. The normalizer must iterate over the validated candidates and check the prefix type against the top of the stack before deciding whether to perform a "push" (nesting) or a "pop" (un-nesting).

---

## 6. Suite 2: Sanitization of Invalid List Structures

In addition to reconstruction, the normalizer must sanitize existing `<ul>` and `<ol>` elements that violate the XHTML content model by containing direct children other than `<li>`.

### 6.1. Orphan Node Detection and Wrapping

1. **Candidate Search:** The engine iterates through all `<ul>` and `<ol>` tags in the document, respecting the Code Shield guard clause.
2. **Orphan Identification:** An "orphan node" is defined as any direct child of a list tag that is not an `<li>`. This includes, but is not limited to, `<p>` tags or `NavigableString` nodes containing non-whitespace characters.
3. **DOM Mutation:**
    * If an orphan node is found, it is extracted from the list.
    * A new, empty `<li>` element is created.
    * The orphan node is appended as a child of this new `<li>`. To maintain block-level semantics, if the orphan is not already a `<p>`, it should be wrapped in one.
    * The newly created `<li>` containing the orphan is re-inserted into the list in its original position.
4. **Container Consistency:** After sanitization, the engine must check if the parent of the list is a `<div class="list-block">`.
    * **MANDATORY DELEGATION:** This check must be performed by first retrieving the parent's `class` attribute and passing it to the `coerce_class_list` core function.
    * If the check fails (the parent is not a `div` or does not contain the `list-block` class), the entire list tag MUST be wrapped in a new `<div class="list-block">` to ensure structural consistency with reconstructed lists.

---

## 7. Suite 3: Fusion of Fragmented Lists

The normalizer must also identify and fuse existing list elements (`<ul>`, `<ol>`) that are logically contiguous but structurally separated by non-semantic "noise" elements (e.g., `<br>`, `<div class="page-break">`).

### 7.1. Fusion Logic

1. **Candidate Search:** The engine iterates through all `<ul>` and `<ol>` tags in the document.
2. **Sibling Scan:** For each list, it scans its immediate following siblings.
3. **Noise Bypass:** It must bypass a configurable set of ignorable noise tags.
4. **Fusion Criteria:** If the next non-noise sibling is a list of the **same type** (e.g., `<ul>` followed by `<ul>`), the lists are fused. The items (`<li>`) of the second list are appended to the first, and the second list and all intermediate noise elements are purged from the DOM.

---

## 8. Output Metadata Contract (YAML)

```yaml
list_normalization:
  unordered_lists_recovered: 8        
  lists_fused: 2
  ordered_lists_recovered: 3          
  multiline_items_welded: 14          
  total_raw_paragraphs_purged: 45     
  status: "success"                   # Canonical PipelineStatus: [success, idle, error]
  execution_timestamp: "2026-07-04T17:50:00Z"

```
