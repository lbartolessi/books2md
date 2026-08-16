# SPECIFICATION: `structural_sanitizer` PACKAGE (Version 2.14 - DETERMINISTIC CLEANUP AND POETIC HEURISTICS)

## 1. Purpose and Scope

This module handles the core normalization of HTML text blocks during Stage 1. To solve execution-order vulnerabilities, it establishes a strict node inspection protocol, ensuring layout markers are safely captured before any destructive cleanup occurs.

**Pipeline Order Contract:** This module **must execute first** within Stage 1, before both `navigation_purger` and `floating_element_processor`. Two hard dependencies enforce this ordering: (1) `navigation_purger`'s `TOC_LINE_RX` regex cannot match across line breaks, so orphan `<br/>` tags fragmenting an index line must already be merged into a single flat string by Step 4 of this module before Pillar 2 can detect it; (2) `floating_element_processor` identifies candidates exclusively via class inspection (`is_floating_element()`), never via raw `style` attributes — so any node marked as floating only through inline CSS (`style="float: left"`) is invisible to it unless this module has already promoted that signal to the `floating-element` class via Step 1.

## 2. Class Interface Contract

```python
from bs4 import BeautifulSoup, Tag
from dom_normalizer.core import BookStyleContext, PipelineStatus
from dom_normalizer.core import get_utc_timestamp, coerce_class_list

class StructuralSanitizer:
    def __init__(self, context: BookStyleContext) -> None:
        self.context: BookStyleContext = context
        self.empty_nodes_purged: int = 0
        self.br_tags_collapsed: int = 0
        self.poetic_br_tags_preserved: int = 0
        self.layout_attributes_persisted: int = 0
        self.inline_floats_normalized: int = 0
        self.inline_indents_normalized: int = 0

```

## 3. Node Execution Flow (The Clockwork Sequence)

Every block-level node must pass through this mandatory, immutable order of operations:

* **Step 1 - Inline Float Fingerprinting:** Invoke `context.normalize_inline_floats(node)`. This traps raw style floats and promotes them to the `floating-element` class. If the node satisfies `context.is_floating_element(node)` after this call, increment `self.inline_floats_normalized`.
* *Deterministic Class Ordering Rule:* If a node accumulates multiple structural classes during the pipeline, they must be ordered with absolute determinism: `blockquote-element` must always precede `floating-element` in the final `class` attribute list.

At the end of this step (or at the end of the node's processing), if the `class` attribute contains multiple elements, the list must be reordered alphabetically or under a fixed criterion where `blockquote-element` always precedes `floating-element`. This ensures immunity against insertion order in text assertions.

* **Step 2 - Structural Indentation Promotion:** Invoke `context.normalize_inline_indents(node)`. If the node satisfies `context.is_blockquote_element(node)`, increment `self.inline_indents_normalized` and tag the node with an internal temporary tracking attribute (`data-bq-promoted="1"`). This acts as an isolation barrier to prevent Step 3 from destroying its inline layout metrics prematurely.
* **Step 3 - The Purge Action & Style Suffix Control:** Scrub presentation-only attributes (`align`, `bgcolor`) and map them to custom `data-orig-*` tracking slots. When processing the `style` attribute:
* If the node is tagged with `data-bq-promoted="1"`, skip layout property destruction in this step to preserve identity validation.
* For all other nodes, **remove only the specific layout properties that have already been captured or promoted** (such as `margin-left`, `padding-left`, `float`, `position`, `align`, `bgcolor`, and `background-color`).
* Any unrecognized, semantic, or presentation-neutral property (e.g., `text-align`, `font-style`) must be left intact within the inline `style` string.
* *Trailing Semicolon Rule:* The reconstructed `style` attribute string must always terminate with a trailing semicolon (`;`) to ensure strict compliance with canonical CSS string formatting.

* **Whitespace-Insensitive Style Filtering:** When parsing inline style properties, each property-value pair must be stripped of all leading and trailing whitespace before evaluation. Properties flagged for removal (`margin-left`, `padding-left`, `float`, `position`, `align`, `bgcolor`, `background-color`) must be discarded cleanly, regardless of any stray spaces or formatting in the original raw HTML string.
* **Step 4 - Whitespace and Tag Collapse (OCR vs. Poetic Guard):** Parse all internal `<br/>` tags. The sanitizer must evaluate whether the node belongs to a protected poetic environment using the following strict sequential resolution:

1. *Semantic Inheritance Check:* If the node or any of its DOM ancestors (parent, grandparent, etc.) contains a `class` attribute matching the substrings `"verse"`, `"poem"`, `"poesia"`, or `"poetic"` (case-insensitive), it is instantly flagged as a protected poetic context.
2. *Metric Fallback Check:* If no semantic class is found in the hierarchy, fallback to textual metrics: the context is poetic if and only if the text fragments contain an average of less than or equal to 12 words per line break AND the node contains a minimum of 2 `<br/>` tags.

* *Execution:* If the context is classified as dirty prose/OCR, the `<br/>` tag must be replaced with a single whitespace (`" "`). Immediately after, to prevent BeautifulSoup from fragmenting the DOM into multiple sibling `NavigableString` nodes, a text consolidation must be invoked on the container (unifying its internal text strings into a single continuous entity).

### Step 5 – Internal Epilogue & Artifact Cleanup

The epilogue MUST execute exactly four sub-passes in strict chronological order after the primary element loop has concluded, ensuring a final deterministic pass over the processed tree:

1. **Tracking Attribute Purge**: Scan the entire document tree and purge all temporary `data-bq-promoted` tracking attributes from the DOM.
2. **Promoted Blockquote Layout Purge**: For any node successfully promoted to the `blockquote-element` class, its inline presentation properties must be stripped to prevent layout duplication (since the class itself now encodes the layout intent).

* *Parser Safety Rule*: To avoid parser-specific multi-value string matching bugs in certain test environments, the class match MUST be evaluated defensively using `coerce_class_list` imported from `core`.

```python
# ❌ CRITICAL ANTI-PATTERN (DO NOT USE - Fails on combined/multi-value classes)
promoted_nodes = soup.find_all(class_="blockquote-element")

# ✅ REQUIRED DEFENSIVE PATTERN (Token Evaluation via coerce_class_list)
promoted_nodes = soup.find_all(
    lambda tag: "blockquote-element" in coerce_class_list(tag.get("class"))
)

```

* *Purge Scope*: Surgically excise ALL properties defined in the global `_LAYOUT_PROPS` set (specifically including `float`, `position`, `margin-left`, and `padding-left`) from the node's `style` attribute. If no presentation-neutral properties remain, the `style` attribute MUST be removed entirely.

1. **Empty-Node Sweep**: Scan and eliminate dead, structurally empty elements using a bottom-up traversal (reverse document order) to ensure nested empty structures collapse correctly, incrementing `self.empty_nodes_purged`. Eligible tags are strictly restricted to the `_PURGEABLE_EMPTY_TAGS` set. A node is defined as safe to remove only if it lacks non-whitespace text content AND contains no media elements (`_MEDIA_TAGS`).
2. **Tree-Wide Text Smoothing (Text Coalescence Enforcement)**: As the absolute final operation before returning the processed soup, the sanitizer must explicitly unify all adjacent `NavigableString` fragments generated by operations like the tag collapse in Step 4.

* *Prettify Guard*: This action consolidates contiguous string nodes into a single continuous text block, explicitly immunizing the output against structural line-breaks forced by BeautifulSoup's `.prettify()` formatter. It ensures that the final prose displays as a single continuous line of physical text without residual breaks or fragmentation artifacts.

## 4. Transformation Examples (Input ──► Output)

### Example A: Selective Style Purging and Class Ordering (SAN_001)

```html
<!-- Input -->
<p style="margin-left: 2.0em; float: left; text-align: justify; font-style: italic;">Prosa</p>

<!-- Output -->
<p class="blockquote-element floating-element" style="text-align: justify; font-style: italic;">
 Prosa
</p>

```

### Example B: Promotion of Inline Indentation and Absolute Cleanup (SAN_002)

```html
<!-- Input -->
<p style="margin-left: 2.5em; padding-left: 0.5em;">Texto blockquote</p>

<!-- Output -->
<p class="blockquote-element">
 Texto blockquote
</p>

```

### Example C: Collapse of Prose Fragmented by Dirty OCR (SAN_003)

```html
<!-- Input -->
<p>Línea partida<br/>por un salto sucio.</p>

<!-- Output -->
<p>
 Línea partida por un salto sucio.
</p>

```

### Example D: Ancestor Class Poetic Guard Inheritance (SAN_004)

```html
<!-- Input -->
<div class="translated-verse"><p>Caminante, no hay camino,<br/>se hace camino al andar.</p></div>

<!-- Output -->
<div class="translated-verse">
 <p>
  Caminante, no hay camino,
  <br/>
  se hace camino al andar.
 </p>
</div>

```

## 5. Canonical Metadata Contract (YAML)

```yaml
structural_sanitization:
  empty_nodes_purged: 14
  br_tags_collapsed: 8
  poetic_br_tags_preserved: 4
  layout_attributes_persisted: 3
  inline_floats_normalized: 2
  inline_indents_normalized: 3
  status: "success"
  execution_timestamp: "2026-07-03T00:31:00Z"

```
