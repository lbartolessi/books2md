# TECHNICAL ARCHITECTURE SPECIFICATION: `heading_normalizer` PACKAGE (Version 2.7 - MICRO-NORMALIZER)

## 1. Purpose and Scope

The `heading_normalizer` package executes semantic realignment and structural healing of document heading hierarchies (`<h1>` through `<h6>`) within the `BeautifulSoup` DOM tree.

* **Execution Stage:** This module runs within **Stage 2 (Semantic Micro-Normalizers)**, operating after Stage 1 sanitization and strictly before structural block partitioning.

* **Design Objectives:**

1. Purge and downgrade presentational "ghost headings" (decorative empty headers used for spatial layout).

2. Enforce a continuous, mathematically valid heading tree navigation sequence, repairing non-contiguous architectural jumps (e.g., an `<h1>` immediately followed by an `<h4>`).

* **Strict Data Invariant:** The module performs in-memory DOM mutations. It is strictly forbidden to output raw Markdown characters (`#`) or inject layout fences.

---

## 2. Runtime Environment & Context Integration

The processor resolves its operational bounds and architectural limits directly from the unified `BookStyleContext` instance injected during initialization:

* **`BookStyleContext.config.initial_heading_level`**: Integer (Default: `1`). Defines the baseline root level for the structural asset file.

* **Core Shield Integration:** Invokes `self._context.is_inside_code_block(node)` as an instance method to instantly bypass text nodes representing literal programming structures.

---

## 3. Two-Pass Normalization Algorithm

The module must execute its processing over the DOM tree using a strict two-pass traversal model to isolate structural cleaning from tree levelling.

```ascii
[Stage 1 Sanitized DOM] ──> (Pass 1: Classification & Purging) ──> (Pass 2: Hierarchy Levelling) ──> [Normalized Headings]

```

### 3.1. Pass 1: Classification and Decorative Purge

The processor evaluates all heading tags (`<h1>` to `<h6>`) present in the document.

1. **Empty/Decorative Target Verification:** If a heading node's structural text—evaluated via `node.get_text(strip=True)`—is completely empty or contains only non-breaking spaces (`&nbsp;`), it is classified as a decorative ghost heading.

2. **Structural Downgrade:** Decorative ghost headings must be converted into standard paragraph blocks wrapped with physical bold attributes to preserve visual intent without polluting the semantic hierarchy tree: `<p><b>[Original Content]</b></p>`.

3. **Format Neutrality:** Text contents of valid headings are preserved natively in the DOM without running ad-hoc character escapes, leaving downstream compilation to the target AST writer.

### 3.2. Pass 2: Continuous Hierarchy Levelling

The processor tracks a cross-file integer state variable `self._current_level`, initialized at instantiation time. It traverses all remaining valid heading nodes sequentially within the current asset file:

0. **Initial State Handling:** If the processor encounters the first heading of a file (i.e., `self._current_level` is still at its initial value of `initial_heading_level - 1`), it must accept the level of this heading as the baseline for the current document. Update state: `self._current_level = n`. This prevents the first heading from being incorrectly re-leveled.

1. **Contiguous Progression ($n == \text{self.\_current\_level} + 1$):** Valid progression step. Update state: `self._current_level = n`.

2. **Structural Re-entry ($n \le \text{self.\_current\_level}$):** Legal branch return to a sibling or parent architectural tier. Update state: `self._current_level = n`.

3. **Invalid Structural Jump ($n > \text{self.\_current\_level} + 1$):** **Hierarchical Fault Detected**. The processor must force an automatic normalization mutation:

* Change the tag name of the element in-place to match the immediate legal contiguous tier: `h{self._current_level + 1}`.

* Log a structural tracking anomaly (`"heading_gap_repaired"`).

* Update state: `self._current_level = self._current_level + 1`.

---

## 4. Concurrency Guardrails & Architectural Separation

To guarantee deterministic hierarchy resolution across multi-threaded pool workers while respecting multi-file book continuity:

* **Cross-File State Persistence:** The tracking state variable `self._current_level` **must live as an instance property** inside `__init__`. It must **never** be reset to its initial value inside the `process()` method execution frame. This ensures that when a book's chapters are distributed across multiple XHTML assets, the structural level depth is perfectly retained from the end of the previous file.

* **Thread Safety via Instance Isolation:** Concurrency protection is strictly guaranteed by the orchestration layer, which allocates exactly one distinct `HeadingNormalizer` instance per book per execution thread.

* **Object Architecture Template:**

```python
from typing import Tuple, List, Dict, Any
from bs4 import BeautifulSoup
from dom_normalizer.core import BookStyleContext

class HeadingNormalizer:
    def __init__(self, context: BookStyleContext):
        self._context = context
        self._config = context.config
        self.anomalies_detected: List[str] = []
        self.headings_purged_count = 0
        self.headings_corrected_count = 0
        
        # PERSISTENCE INVARIANT: State lives here to maintain cross-file hierarchy
        self._current_level: int = self._config.initial_heading_level

    def process(self, soup: BeautifulSoup) -> Tuple[BeautifulSoup, dict]:
        """Executes heading hierarchy enforcement on the provided DOM soup."""
        if self._context.is_inside_code_block(soup):
            return soup, {"status": "idle"}

        self._execute_decorative_purge(soup)
        self._execute_hierarchy_levelling(soup)

        # Metadata compilation and return
        ...

    def _execute_decorative_purge(self, soup: BeautifulSoup) -> None:
        """Pass 1: Downgrades empty ghost headings to standard bold paragraphs."""
        ...

    def _execute_hierarchy_levelling(self, soup: BeautifulSoup) -> None:
        """Pass 2: Enforces linear progressive structural tree steps without resetting instance state."""
        ...
