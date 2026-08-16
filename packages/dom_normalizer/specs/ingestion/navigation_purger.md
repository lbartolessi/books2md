# SPECIFICATION: `navigation_purger` PACKAGE (Version 2.16 - ANTI-HEURISTIC LOCKDOWN)

## 1. Purpose and Scope

This module detects, isolates, and purges redundant navigation structures from the DOM tree. By executing prior to text slicing, it prevents tables of contents, index matrices, and link arrays from polluting narrative chunks.

**Pipeline Order Contract:** This module executes in Stage 1, strictly **after `structural_sanitizer`** (whose line-merging pass is a hard prerequisite for `TOC_LINE_RX` to match index lines fragmented by orphan `<br/>` tags) and **before `floating_element_processor`**.

---

## 2. Class Interface Contract

```python
import re
from bs4 import BeautifulSoup, Tag
from dom_normalizer.core import BookStyleContext, PipelineStatus
from dom_normalizer.core import get_utc_timestamp, coerce_class_list

class NavigationPurger:
    _FILE_FALLBACK_RX = re.compile(r'/(nav|toc|indice|contents|summary)\.e?xhtml$', re.IGNORECASE)
    _TOC_LINE_RX = re.compile(r'^.{3,70}(?:\.{2,}|\s+|\-+|(?<!\d)\.)\d+(?:[\s,;\-]*\d*)\s*$')

    def __init__(self, context: BookStyleContext) -> None:
        self.context: BookStyleContext = context
        self.native_toc_isolated: bool = False
        self.inline_toc_blocks_purged: int = 0
        self.tabular_indexes_purged: int = 0
        self.chars_removed_count: int = 0
        self.elements_evaluated_count: int = 0

```

---

## 3. The Three Pillars of Detection & Core Imperatives

### Pillar 1: Native EPUB3 Identification & Tier 2 Safe Fallback

* **Tier 1 (Semantic):** Direct isolation of elements bearing `epub:type="toc"`, `role="doc-toc"`, or native `<nav>` structures.
* **Tier 2 (Mandatory File Fallback Gate):** If a file name matches `_FILE_FALLBACK_RX` (e.g., `toc.xhtml`), the system evaluates the **Text-to-Link Character Ratio (TLCR)** over the entire body:

$$\text{TLCR} = \frac{\text{Character count outside any } \langle a \rangle \text{ tag}}{\text{Total character count within the } \langle body \rangle}$$

* **CRITICAL STRUCTURAL OVERRIDE (Anti-Decomposition Guard):** Before applying or evaluating the numerical TLCR threshold, the implementation **MUST** check if the body contains any container elements with protective narrative classes (specifically `"prose"`, `"editorial"`, or `"editorial-prose"`).
* *BeautifulSoup Implementation Constraint:* Because BeautifulSoup parses the `class` attribute into a list of strings under specific parsing modes, direct string comparisons like `node.get('class') == 'prose'` are volatile and unsafe. To eliminate discrepancies, the implementation **MUST** normalize the class token payload using `coerce_class_list()` from core.py before verifying inclusion:

```python
any(c in ['prose', 'editorial', 'editorial-prose'] for c in coerce_class_list(node.get('class')))

```

* If a protective container is detected, the file **MUST** bypass *Pure Index Mode* and be forced into **Mixed Content Mode**, overriding any mathematical TLCR value.
* **Pure Index Mode (TLCR < 0.85 AND no Protected Prose Containers):** The file consists almost entirely of navigation nodes. Safely clear/purge the entire `<body>` container.
* **Mixed Content Mode (TLCR >= 0.85 OR Protected Prose Containers Present):** The file contains mixed text and narrative elements. The system **strictly forbids** purging the entire `<body>`. Instead, Tier 2 **MUST** abort the broad truncation and **delegate execution to Pillars 2 and 3** to perform micro-structural scanning (line by line), removing only localized index arrays while protecting embedded prose.

### Pillar 2: Contiguous Run Algorithm (Inline TOC Detector)

To destroy embedded indexes without injuring sequential data points or lists, the processor runs a sliding-window sweep:

1. **Shield Verification:** Check `self.context.is_inside_code_block(node)`. If true, bypass.
2. **Line Match:** Lines are matched against `self._TOC_LINE_RX`.
3. **Sliding Window:** Contiguous sibling nodes matching the regex are grouped. The run aborts instantly if it hits an **Air-Lock** (any text block >30 words), a heading (`<h2>`), or parent container boundaries.
4. **Threshold Gate:** If the contiguous group contains fewer than 4 lines ($M < 4$), it is rejected and preserved intact.
5. **The Agnostic Anti-Step Guard:** For runs >= 4 lines, the trailing page digits are parsed into an evaluation array:

* **Arithmetic Progressions Check:** If the integers form a sequential progression increasing by exactly $+1$ starting at 0 or 1 (e.g., `[1, 2, 3, 4]`), it is classified as an instruction checklist or timeline and **preserved**.
* **Purge Execution:** If the sequence displays broken deltas or non-linear jumps, it is certified as an embedded index and stripped.

### Pillar 3: Agnostic Tabular Indexes (Strict Deterministic Rules)

To prevent implementation divergence or the usage of arbitrary statistical thresholds (such as "80% rule" or "mostly increasing" heuristics), every `<table>` element **MUST** be evaluated under a strict, non-negotiable binary contract. A table is classified as an index and purged if and only if it complies with the following sequence:

1. **Row Count Gate:** The table **MUST** contain at least 2 row (`<tr>`) elements.
2. **Initial Column Constraint:** For every single row in the table, the first inner cell (`<td>` or `<th>`) **MUST** have a stripped text string length strictly under 25 characters (`len(text.strip()) < 25`). If *any* single row exceeds this limit, the entire table is ruled as layout/data content and **MUST NOT** be purged.
3. **Final Column Numeric Extraction:** For every single row, the last inner cell (`<td>` or `<th>`) **MUST** contain a page marker. The implementation **MUST** extract the first contiguous block of digits (`\d+`) found in that cell. If any final cell contains text but lacks any numeric digit, the table **MUST** be preserved intact.
4. **Strict Monotonicity Rule (Zero Statistical Tolerance):** Let the extracted integers form an ordered array $U = [p_1, p_2, \dots, p_n]$. The implementation **MUST** verify that $U$ follows a strict non-decreasing monotonic progression, where every element is greater than or equal to the previous one ($p_i \le p_{i+1}$).

* *No Approximations:* Approximate match ratios, percentage-based thresholds, or error tolerances for numbering resets are **strictly prohibited**.
* If $U$ is strictly non-decreasing, the table is certified as an index: decompose the `<table>` element, calculate its character length into `self.chars_removed_count`, and increment `self.tabular_indexes_purged`. Otherwise, leave it untouched.

---

## 4. Transformation Examples (Input ──► Output)

### Example C: Mixed Content File triggering Tier 2 Fallback (Delegation Flow)

```html
<!-- Input (File: contents.xhtml) -->
<body>
  <h1>Tabla de Contenidos</h1>
  <p><a href="ch1.xhtml">Capítulo I. La Arqueología del Saber</a>...................11</p>
  <p><a href="ch2.xhtml">Capítulo II. Las Reglas del Habitus</a>....................45</p>
  <div class="prose">
    <h2>Nota del Editor</h2>
    <p>Esta compilación reúne textos fundamentales.</p>
  </div>
</body>

<!-- Output -->
<body>
  <h1>Tabla de Contenidos</h1>
  <div class="prose">
    <h2>Nota del Editor</h2>
    <p>Esta compilación reúne textos fundamentales.</p>
  </div>
</body>

```

### Example D: Pillar 3 - Tabular Index Purge Execution

```html
<!-- Input (Table layout fulfilling all metrics: short labels + monotonic page progression) -->
<table class="index-matrix">
  <tr>
    <td>Prefacio</td>
    <td>Pág. 5</td>
  </tr>
  <tr>
    <td>Introducción General</td>
    <td>Pág. 12</td>
  </tr>
  <tr>
    <td>Sistemas Complejos</td>
    <td>Pág. 45</td>
  </tr>
</table>

<!-- Output (Decomposed completely) -->

```

---

## 5. Canonical Metadata Contract (YAML)

```yaml
navigation_purging:
  native_toc_isolated: bool
  inline_toc_blocks_purged: int
  tabular_indexes_purged: int
  chars_removed_count: int
  elements_evaluated_count: int
  status: "success" | "idle" | "error"
  execution_timestamp: "YYYY-MM-DDTHH:MM:SSZ"

```
