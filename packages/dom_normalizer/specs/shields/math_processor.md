# TECHNICAL ARCHITECTURE SPECIFICATION: `math_processor` PACKAGE (v2.7)

## Version 2.7 — Non-Destructive Hybrid Math Normalization (Pandoc-Optimized)

### 1. Purpose and Scope

The `math_processor` package is a format normalization engine (Stage 2 - Document Structure Layer) whose sole task is to prepare and structure the mathematical expressions present in the XHTML so that **Pandoc** can process them natively in the AST (Abstract Syntax Tree) without losing semantic information or enriched visual assets (diagrams, colors, or legends).

- **Execution Invariant:** It operates strictly in local memory using BeautifulSoup4 in an air-gapped manner, free from network microservices, fully integrated under the unified `BookStyleContext` framework (core).
- **Pipeline Order Contract:** This module runs strictly after structural layout blocks are processed (such as `table_normalizer` and `blockquote_processor`) to ensure mathematical expressions inside complex tables or blockquotes are evaluated within their final consolidated structural containers.
- **RAG Integration:** The final result ensures that the LaTeX text is indexable/vectorizable, while the original graphical content remains available to be retrieved and fully integrated into the end-user interface.

---

### 2. Simplified Decision Matrix (Ockham's Razor)

The processor analyzes the DOM tree nodes by applying a three-way sequential logic based on data availability, discarding complex visual analysis heuristics:

```ascii
                  [Expression / Graphic Node]
                                │
                    (Is it inside code?)
                                ├── YES ──► [Bypass / Pass-through]
                                ▼ NO
     ┌──────────────────────────┴──────────────────────────┐
     ▼                                                     ▼
Is it a <math> tag?                                  Is it an <img> / <svg> tag?
│                                                     │
▼                                                     ▼
(Native MathML)                                     Does it have LaTeX metadata?
│                                            (data-latex, data-math, strict alt)
▼                                                     │
[CASE B: LATEX ONLY]                                           ├── NO ──► [CASE A: IMAGE ONLY]
(XSLT Transformation)                                          │          (Bypass / Pass-through)
▼                                                              ▼
[CASE C: BOTH] ◄───────────────────────────────────────────────┘
(Hybrid Coexistence)

```

#### 2.1. CASE A: Image Only (Blind images or pure diagrams)

- **Condition:** The node is an `<img>` or `<svg>`, but its attributes do not contain any recoverable mathematical syntactic representation.
- **Action:** **Absolute Bypass (Pass-through).** The module does not alter the node. It is assumed to be a generic illustration, an ornament, or a descriptive graphic whose direct textual interpretation exceeds the scope of the local parser. It is fully delegated to Pandoc to convert it into a standard image tag in Markdown (`!`).

#### 2.2. CASE B: Mathematical Expression Only (Pure MathML)

- **Condition:** A structured `<math>` block is found without associated fallback images.
- **Action:** The MathML tree is compiled locally by passing it through a standard XSLT transformation sheet (` .etree.XSLT`) to translate it into a clean LaTeX text string. Visual style attributes (like `mathsize` or `mathcolor`) are purged.
- **Error Handling & Fallback:** If the MathML source is malformed or the XSLT engine encounters a compilation anomaly, the processor catches the exception, logs a standard system warning using the python `logging` infrastructure, and falls back to wrapping the raw text safely inside a standard structural block, preventing pipeline failures.
- **Insertion:** Replaces the `<math>` block with a wrapped HTML structure according to its layout:
- Inline: `<span class="math-inline">$ \alpha + \beta $</span>`
- Block: `<div class="math-block">$$\frac{a}{b}$$</div>`

#### 2.3. CASE C: Both (Image + available LaTeX)

- **Condition:** The node contains a graphic asset (`<img>` or `<svg>`), but retains its mathematical counterpart in its explicit configuration attributes (`data-latex`, `data-math`), or an `alt` attribute strictly containing explicit LaTeX structural tokens (defined as raw strings, e.g., `r'\frac'`, `r'\int'`, `r'^{'`).
- **Action:** **Hybrid Coexistence (Non-destructive).** The image is not removed, as it may contain critical visual information (explanatory arrows, associated graphs, highlighted typography). The processor wraps both elements, preserving their nature:
- **Block vs. Inline Heuristic:** The processor MUST apply a heuristic to determine the layout context of the image:
  - An image is considered **block-level** if its parent is not a `<p>` tag, OR if its parent is a `<p>` tag that contains no other significant text content.
  - In all other cases, it is considered **inline**.
- **DOM Mutation:**
  - If it is a block, they are grouped within a `<div class="math-block">` container.
    - **Crucial Detail:** If the block-level image was inside a wrapper `<p>`, the entire `<p>` tag is replaced by the new `<div>`, and the image is moved inside it.
  - If it is inline, they are grouped within a `<span class="math-inline">` container.

---

### 3. Formatting Contracts for Pandoc (Markdown Output)

To ensure the polymorphic behavior of the document, the mutated outputs in the DOM will follow these Markdown templates that Pandoc digests perfectly:

#### 3.1. Output for Block Formulas (Display Block)

```markdown
:::{.math-block}

$$
\int_{a}^{b} f(x) \,dx = F(b) - F(a)
$$

![Explanatory graph of the differential equation](quantum_mechanics/images/ch01/equation_visual.png){width=50%}
:::
```

#### 3.2. Output for Inline Formulas

If coexistence occurs in the middle of a paragraph, they are arranged contiguously within the same protected span to safeguard both the LaTeX text and the graphic asset from any artificial line break:

```markdown
The body's velocity is defined by the state vector [$ \vec{v} = \frac{d\vec{r}}{dt} $ !]{.math-inline} where t is time.
```

---

### 4. Technical Implementation Mandates

To ensure robustness, security, and maintainability, the implementation must adhere to the following technical contracts:

- **`lxml` Dependency Management:**
  - The `lxml` library is required for XSLT transformation. The implementation MUST treat it as an optional dependency.
  - If `lxml` is not found at runtime, a warning MUST be logged, and the MathML-to-LaTeX conversion capability (Case B) MUST be disabled. The processor will continue to operate, handling only hybrid images (Case C).
- **Secure XML Parsing:**
  - All XML parsing operations using `lxml` (e.g., `etree.fromstring`) MUST use a secure parser configuration that explicitly disables external entity resolution and network access (`resolve_entities=False`, `no_network=True`) to mitigate XXE (XML External Entity) vulnerabilities.
- **DOM Mutation with BeautifulSoup:**
  - When creating new HTML tags, the `attrs` dictionary (e.g., `soup.new_tag('div', attrs={'class': 'my-class'})`) MUST be used for assigning CSS classes.
  - **Rationale:** While the `class_` keyword argument is idiomatic, recent versions of BeautifulSoup (e.g., 4.15.0) have shown regressions where this argument is rendered literally as a `class_` attribute, causing test failures. The `attrs` dictionary is a more robust and backward-compatible approach.
- **Performance and Logging:**
  - All logging calls, especially within loops or exception blocks, MUST use lazy formatting (e.g., `logging.warning("Error processing node: %s", node_id)`) instead of f-strings to optimize performance.
- **Pattern Definition:**
  - All regular expressions or string patterns containing backslashes, such as LaTeX commands, MUST be defined using raw strings (e.g., `r'\frac'`) to prevent `SyntaxWarning` and ensure correct interpretation.

---

### 5. Algorithmic Implementation Template

```python
import re
import logging
from typing import Tuple
from bs4 import BeautifulSoup, Tag
from dom_normalizer.core import BookStyleContext, PipelineStatus
from dom_normalizer.core import get_utc_timestamp

class MathProcessor:
    """
    Normalizes the mathematical flow from EPUB to Markdown non-destructively,
    ensuring the coexistence of LaTeX representations and enriched images.
    """
    def __init__(self, context: BookStyleContext):
        self.context = context
        self.equations_converted = 0
        self.hybrid_blocks_created = 0

    def _extract_latex_from_attributes(self, tag: Tag) -> str:
        """Searches for LaTeX traces in the accessibility attribute hierarchy."""
        # Direct explicit mathematical markers take immediate priority
        for attr in ['data-latex', 'data-math']:
            value = tag.get(attr, '')
            if value:
                return value.strip()

        # Strict validation constraint for generic alt tags to prevent filename/hyphen false positives
        alt_value = tag.get('alt', '')
        if alt_value:
            strict_latex_patterns = [r'\frac', r'\int', r'\alpha', r'^{', r'_{', r'\vec', r'\sum']
            if any(pattern in alt_value for pattern in strict_latex_patterns):
                return alt_value.strip()
        return ''

    def process(self, soup: BeautifulSoup) -> Tuple[BeautifulSoup, dict]:
        """
        Scans the DOM applying local non-destructive transformations.
        """
        # 1. Process <math> blocks (Case B)
        for math_tag in soup.find_all('math'):
            # Code Shield Guard Clause
            if self.context.is_inside_code_block(math_tag):
                continue

            try:
                # [Local XSLT conversion logic with internal error isolation]
                self.equations_converted += 1
            except Exception as e:
                logging.warning("XSLT compilation failed for MathML block: %s", e)
                continue

        # 2. Process hybrid images (Case C)
        for img_tag in soup.find_all(['img', 'svg']):
            # Code Shield Guard Clause
            if self.context.is_inside_code_block(img_tag):
                continue

            latex_str = self._extract_latex_from_attributes(img_tag)
            if latex_str:
                # Modify the DOM to inject the hybrid coexistence structure
                self.hybrid_blocks_created += 1
            else:
                # Case A: Image only. Ignored (Pass-through)
                continue

        status_value = PipelineStatus.SUCCESS.value if (self.equations_converted + self.hybrid_blocks_created) > 0 else PipelineStatus.IDLE.value

        metadata = {
            "math_processing": {
                "equations_normalized": self.equations_converted,
                "hybrid_blocks_structured": self.hybrid_blocks_created,
                "status": status_value,
                "execution_timestamp": get_utc_timestamp()
            }
        }
        return soup, metadata

```

---

### 6. Output Metadata Contract (YAML)

```yaml
math_processing:
  equations_normalized: 8 # MathML expressions converted to pure LaTeX
  hybrid_blocks_structured: 12 # Mixed blocks (Image + LaTeX) successfully encapsulated
  status: "success" # Allowed values matching PipelineStatus Enum: success, idle, error
  execution_timestamp: "2026-06-30T17:15:00Z"
```
