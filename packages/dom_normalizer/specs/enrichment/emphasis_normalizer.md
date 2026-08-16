# TECHNICAL ARCHITECTURE SPECIFICATION: `emphasis_normalizer` PACKAGE (Version 2.3 - MICRO-NORMALIZER)

## 1. Purpose and Scope

The `emphasis_normalizer` package eliminates stylistic dispersion, redundant nesting, and typographical chaos across the document DOM tree by flattening and translating raw inline styles and presentation tags into a strict binary semantic format.

* **Execution Stage:** This module runs within **Stage 2 (Semantic Micro-Normalizers)**, executing adjacent to the heading normalizer.
* **Target Canonical State:** All stylistic variations of emphasis must map to exactly two canonical physical XHTML tags:
  * **Italic Layouts:** Unified under the lowercase physical tag `<i>`.
  * **Bold Layouts:** Unified under the lowercase physical tag `<b>`.
* **Strict Constraints:** The use of uppercase tags (`<I>`, `<B>`) is strictly prohibited. Raw Markdown style markers (`*`, `**`, `_`) must never be injected directly into text flows during this stage.

## 1.1. Pipeline Order Contract

This module executes *after* `heading_normalizer` and *before*`blockquote_processor`.

---

## 2. Runtime Dependency Integration

* **Exclusion Protocol:** `self.context.is_inside_code_block(node)`.
* **Molecular Matching Engine:** italic/bold detection reuses `BookStyleContext`'s
  existing CSS-harvesting infrastructure (`self.context.is_italic_element(node)`,
  `self.context.is_bold_element(node)`) rather than a bespoke class matrix.

```python
from bs4 import BeautifulSoup, Tag
from typing import Tuple
from dom_normalizer.core import BookStyleContext, PipelineStatus
from dom_normalizer.core import get_utc_timestamp

class EmphasisNormalizer:
    def __init__(self, context: BookStyleContext) -> None:
        self.context = context
        self.italic_nodes_normalized = 0
        self.bold_nodes_normalized = 0
        self.semantic_resets_triggered = 0

    def process(self, soup: BeautifulSoup) -> Tuple[BeautifulSoup, dict]:
        if self.context.is_inside_code_block(soup):
            return soup, {"status": PipelineStatus.IDLE.value}

        self._normalize_native_tags(soup)
        self._traverse_with_emphasis_state(soup, "normal")

        status = PipelineStatus.SUCCESS.value if (
            self.italic_nodes_normalized + self.bold_nodes_normalized
        ) > 0 else PipelineStatus.IDLE.value

        metadata = {
            "emphasis_normalization": {
                "italic_nodes_normalized": self.italic_nodes_normalized,
                "bold_nodes_normalized": self.bold_nodes_normalized,
                "semantic_resets_triggered": self.semantic_resets_triggered,
                "contrastive_detection_disabled": False,
                "status": status,
                "execution_timestamp": get_utc_timestamp()
            }
        }
        return soup, metadata
```

---

## 3. Transformation & Nesting Resolution Rules

### 3.1. Pre-existing Tag Normalization

Native XHTML tags that declare emphasis (`<em>`, `<strong>`, `<ins>`) must be normalized before processing inline style properties. `<em>` tags are converted to `<i>`, and `<strong>` tags are converted to `<b>`.

### 3.2. Nesting Hierarchy and Contrastive Emphasis Resolution

The engine tracks a cascading state variable `current_emphasis_state`
(`normal` | `italic` | `bold` | `italic+bold`), inherited top-down through
the DOM exactly like `LanguageTagger`'s `current_context_lang` — a node's
active state propagates to all its descendants unless a mutation changes it
for that specific subtree.

#### 3.2.1. Bi-directional Nesting (Canonical Order)

If a text segment requires both bold and italic emphasis — whether from a
direct style/class match (Category 3) or from a contrastive decision
(§3.3.3) — the italic container is always the outer structural parent:
`<i><b>[Content]</b></i>`. This canonical order is the single source of
truth for both opening and closing sequences; no other ordering is ever
produced anywhere in this module.

#### 3.2.2. Redundant Nesting Purge

Identical adjacent or nested emphasis tags (e.g., `<i><i>text</i></i>`)
produced by malformed source markup are flattened into a single atomic
wrapper before contrastive analysis begins.

#### 3.2.3. Contrastive Emphasis Detection (Category 4)

Scope restriction: this detection applies **exclusively to text within
`<p>` elements**. Heading tags (`<h1>`–`<h6>`) are never evaluated — their
semantic weight is already established by heading level, and applying
contrastive emphasis logic there would produce meaningless nested markup.

A text run inside a `<p>` is flagged as an emphasis-by-contrast candidate
if, relative to the paragraph's established base typography, it exhibits:

* **A different `font-family`** than the base, in either direction (no
  magnitude threshold — any declared difference counts), OR
* **A larger `font-size`** than the base (any positive difference counts).

A **smaller** `font-size` alone is explicitly *not* a trigger — deliberately
biased toward under-flagging, since undersized text is frequently a layout
artifact (legal disclaimers, running footers) rather than genuine emphasis,
and this module follows the project-wide conservative principle: a missed
emphasis costs nothing, a spurious one corrupts real prose.

*Base typography resolution:* since EPUB reading systems have no mandated
default stylesheet (see W3C epub-specs#672), no external fallback value is
ever assumed, and — critically — **absence of a declared baseline is not
itself treated as a baseline**.

* If the stylesheet declares `font-family`/`font-size` for the `p`
  selector (or `body`, as fallback), that declared value becomes the
  baseline, and Category 4 (contrastive typography) detection proceeds
  normally per §3.3.3–3.3.5.
* If neither `p` nor `body` declares a value, Category 4 detection is
  **disabled entirely for that document**. The module falls back to
  Categories 1-3 only (direct `font-style`/`font-weight` matching).
  Treating the absence of a baseline as license to flag any font variation
  risks flagging incidental styling artifacts from editorial/OCR tooling
  (residual inline `font-family` spans with no semantic intent) across the
  entire book — exactly the kind of spurious, book-wide false positive
  this project's conservative-bias principle exists to prevent.

This decision is recorded in telemetry (`contrastive_detection_disabled:
bool`) so it remains auditable rather than a silent no-op, consistent with
how `poetry_normalizer` surfaces its own rejection mechanisms
(`dialogue_blocks_excluded`, `geometric_rejections`).  

#### 3.2.4. Application Rule (State Transition Table)

| `current_emphasis_state` | Category 4 match resolves to |
| --- | --- |
| `normal` | `<i>[Content]</i>` |
| `bold` | `<i><b>[Content]</b></i>` |
| `italic` | `<i><b>[Content]</b></i>` |
| `italic+bold` | **Semantic Reset** (§3.3.5) |

#### 3.2.5. Semantic Reset (Tree Partition Operation)

Unlike every other rule in this section, Semantic Reset is not a local
wrap — it is a **split of the active `<i><b>` ancestor pair** around the
contrastive segment, so the segment renders in plain text by visual
contrast with its still-emphasized surroundings.

Given a contrastive text run $T$ discovered while `current_emphasis_state
== italic+bold`, with the active ancestor pair `<i><b>[...]</b></i>`
wrapping a larger content block:

1. Locate the nearest active `<i>`/`<b>` ancestor pair (the pair whose
   combined effect produced the current `italic+bold` state — this may
   itself be the product of a prior, outer Semantic Reset re-opening;
   nesting can compound recursively).
2. Partition the wrapped content into three ordered parts: *before* $T$,
   $T$ itself, and *after* $T$.
3. Reconstruct two independent copies of the `<i><b>...</b></i>` wrapper —
   one containing *before*, one containing *after* — and place $T$ as a
   plain sibling node between them, with no wrapper of its own.
4. Result: `</b></i>` immediately before $T$, `<i><b>` immediately after
   it — closing and reopening in the exact canonical order from §3.3.1,
   never inverted.
5. `current_emphasis_state` for any nodes nested *inside* $T$ itself
   resets to `normal` for the duration of that segment, then reverts to
   `italic+bold` for the reopened *after* wrapper.

Each execution of this operation increments `self.semantic_resets_triggered`

---

## 4. Output Metadata Contract (YAML)

The processing execution dictionary returned by this module must conform exactly to the following serialization schema:

```yaml
emphasis_normalization:
  italic_nodes_normalized: 24
  bold_nodes_normalized: 12
  semantic_resets_triggered: 1
  contrastive_detection_disabled: false   # true si no había baseline declarado para p/body
  status: "success"
  execution_timestamp: "..."
```
