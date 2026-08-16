# SPECIFICATION: POETRY NORMALIZER ENGINE AND DETERMINISTIC VERSE CONVERSION (v2.6 - PURE GEOMETRIC PRODUCTION)

## 1. Scope and Ingestion Pipeline

This document establishes the production-grade specification for the `PoetryNormalizer` class architecture, operating within the unified `BookStyleContext` framework (core). It unifies forensic structural matching and automated ingestion controls to isolate and process lyric layouts within HTML/XHTML documents while ensuring standard prose remains strictly unaffected.

The engine optimizes document scanning via automated entry gates:

* **Header Metadata Filter (`metadata.opf`):** Upon EPUB ingestion, the pipeline inspects the manifest file. If lyric terms are detected within the `<dc:type>`, `<dc:subject>`, or `<dc:description>` fields, the document is flagged as **"High Poetry Priority"**. This flag is explicitly consumed by the execution layer to enable global heuristic scans of unlabelled block clusters.
* **Universal Blockquote Inspection (`<blockquote>`):** Regardless of metadata flags or whether the book is flagged as a poetry volume, the engine universally intercepts all `<blockquote>` nodes across all documents in the library catalog for isolated structural verse verification.
* **Explicit Guard Clause (Pass-Through Filter):** Interception is limited to inspection only. If an intercepted block fails the quantitative validation metrics (Section 5), the engine immediately aborts mutation and **returns the node entirely intact to the original prose stream**, ensuring absolute immunity for academic citations and epigraphs.

### 1.1. Pipeline Order Contract

To resolve execution jurisdiction without structural race conditions, the engine is governed by a strict sequential ordering constraint:

* **The Dependency:** `PoetryNormalizer` **must execute strictly after** `blockquote_processor` has completed its structural pass.
* **The Rationale:** This contract ensures that the Universal Blockquote Inspection operates over the complete population of citations—both native tags inherited from the raw XHTML and reconstructed containers built dynamically by structural strategies (e.g., `ProseQuoteStrategy` or `EnclosedQuotationStrategy`).

---

## 2. StructuralMatcher API

The `StructuralMatcher` identifies structural patterns using forensic traits defined in an external JSON pattern registry. It acts strictly as a read-only, non-mutating observer of the DOM tree.

### 2.1. Initialization

```python
from dom_normalizer.core import BookStyleContext

class StructuralMatcher:
    def __init__(self, context: BookStyleContext):
        """
        Initializes the matcher with the unified BookStyleContext instance.
        Resolves configurations, thresholds, and paths directly through the context's
        EngineConfiguration to enforce clean Inversion of Control (IoC).
        
        Note: structural_registry_path (str), br_density_threshold (float),
        dialogue_exclusion_threshold (float), and enjambment_ratio_threshold (float)
        are explicitly appended as native fields within the EngineConfiguration 
        dataclass in core.py. All four are PROVISIONAL defaults pending
        empirical calibration against a representative multilingual corpus sample
        (see Calibration Notes in §3.4 and §4.2/4.3). br_density_threshold in
        particular is under active reconsideration as a global absolute constant
        and may be superseded by a per-book relative metric in a future revision.
        """
        self.context = context
        self.registry_path = context.config.structural_registry_path
        self.br_density_threshold = context.config.br_density_threshold
        self.dialogue_exclusion_threshold = context.config.dialogue_exclusion_threshold
        self.enjambment_ratio_threshold = context.config.enjambment_ratio_threshold
```

### 2.2 Contrato de match() con razón de rechazo explícita

```python
def match(self, target: Tag) -> Dict[str, Any]:
    """
    Analyzes the target tag against the registry traits.
    
    Returns:
    {
        "match_type": "exact" | "structural" | "none",
        "registry_key": str | None,
        "matching_mode": "container" | "table" | "separator" | None,
        "rejection_reason": "dialogue_excluded" | "geometric_mismatch" | None
    }
    
    `rejection_reason` is populated only when match_type == "none" AND the
    candidate reached separator-mode evaluation (i.e., it was not rejected
    earlier by container/table mode mismatch). It distinguishes rejections
    caused by the Dialogue Exclusion Guard (§3.4) from rejections caused by
    both conditions of the Compound Classification Rule (§4.3) failing
    simultaneously. This granularity is required for corpus-based threshold
    calibration: without it, false negatives observed during calibration
    cannot be attributed to a specific mechanism.
    """
```

---

## 3. Quantitative Pattern Trait Rules

A node triggers a structural match if its geometric composition matches one of three structural modes:

### 3.1. `container` Mode

Triggers if the element matches explicit signature tags or classes defined in the structural pattern registry. It represents wrappers designed specifically to house verses.

### 3.2. `table` Mode

Triggers if the target fragment is a `<table>` element that strictly satisfies a nested hierarchical structural `AND` condition: it must contain at least one row element (`<tr>`), which in turn must explicitly host at least one cell element (`<td>`). This prevents isolated or orphaned cell fragments from triggering false poetry matches.

### 3.3. `separator` Mode

Triggers if the layout exhibits high-density lines isolated by structural markers. To remain consistent with the pipeline execution order, since the Stage 1 `structural_sanitizer` collapses internal `<br/>` elements into standard spaces inside standard `<p>` nodes, the `separator` mode operates strictly by evaluating continuous sequences of independent sibling `<p>` tags as its primary data stream, verifying if their line-length constraints mirror a lyric configuration.

### 3.4. Dialogue Exclusion Guard (Pre-Filter)

Before any density or enjambment metric is computed, the candidate sequence of
sibling `<p>` elements MUST pass through a structural dialogue exclusion filter.
This guard exists because theatrical dialogue and dramatized prose naturally
exhibit short, line-broken structures that are geometrically indistinguishable
from verse under a pure length-based metric, yet must never be mutated into
`poetry-block` structures.

**Detection Signatures:**

```python
DIALOGUE_DASH_RX = re.compile(r'^[—–\-]')
SPEAKER_LABEL_RX = re.compile(r'^[A-ZÁÉÍÓÚÑÀÈÌÒÙÄÖÜ][A-ZÁÉÍÓÚÑÀÈÌÒÙÄÖÜ\s]{1,30}[.:]\s')
```

* `DIALOGUE_DASH_RX` matches lines opening with an em-dash, en-dash, or hyphen
  followed by whitespace — the standard typographic convention for dialogue
  turns in the French and Spanish literary tradition.
* `SPEAKER_LABEL_RX` matches lines opening with an uppercase character name
  followed by a period or colon — the standard playscript convention for
  speaker attribution (e.g., `"HAMLET:"`, `"ELVIRA."`).

**Exclusion Rule:** If the proportion of `<p>` elements in the candidate
sequence matching either signature exceeds `dialogue_exclusion_threshold`
(provisional default: 0.40), the entire sequence is immediately rejected and
returned to the pass-through guard clause. No further geometric or
statistical evaluation is performed. This check takes strict precedence over
both `container` and `separator` mode matching.

*Calibration Note:* The threshold is deliberately asymmetric toward
exclusion — mixed dialogue/narration passages (where a narrator's paragraph
interleaves with short dialogue lines) should still be rejected even when not
every single line matches, since destructive misclassification of dramatized
prose is the costlier failure mode under the module's conservative-bias
principle.

---

## 4. Quantitative Metric Computations

### 4.1. Line Density (short-line verse detector)

$$\text{Line Density} = \frac{\text{Total character length of trimmed text inside node}}{\text{Total count of structural line segments}}$$

If the calculated ratio falls below `br_density_threshold`, the sequence is
flagged as short-line lyric or itemized content. As previously established,
this metric alone systematically under-detects long-line free verse
(Aleixandre, Whitman, Dámaso Alonso, the French surrealists), where
individual lines routinely exceed ordinary prose-paragraph density.

### 4.2. Enjambment Ratio (long-line verse detector)

To recover recall on the long-line register, a second, orthogonal geometric
signal is computed independently of line length:

$$\text{Enjambment Ratio} = \frac{\text{Count of lines NOT ending in terminal punctuation} \; (. \; ! \; ? \; \ldots)}{\text{Total count of structural line segments}}$$

A line is considered "closed" only if its trimmed text ends in a
sentence-terminal mark (`.`, `!`, `?`, `…`, optionally followed by a closing
quotation character). Any other ending — including comma, semicolon, colon,
or no punctuation at all — counts as "open" for this computation.

This is a geometric proxy for enjambment, not a syntactic one: it makes no
claim about grammatical continuation, only about the surface-level absence of
sentence-closing punctuation at line boundaries. Justified prose paragraphs
are near-universally composed of complete sentences and therefore exhibit a
low Enjambment Ratio; verse — especially the long-line free verse register —
regularly lets syntax spill across line breaks and therefore exhibits a high
ratio, independent of how long the individual lines are.

### 4.3. Compound Classification Rule

A candidate sequence that has survived the Dialogue Exclusion Guard (§3.4) is
classified as a `separator` mode match if it satisfies **at least one** of
the following two independent conditions:

(a) **Line Density** falls below `br_density_threshold`
    (captures conventional short-line verse; by design, this also catches
    prosaic itemized content such as lists — the poem/list distinction is
    explicitly out of scope for this module, per its non-semantic mandate), OR

(b) **Enjambment Ratio** exceeds `enjambment_ratio_threshold`
    (captures long-line free verse, where Condition (a) alone systematically
    fails).

*Calibration Note:* `enjambment_ratio_threshold` requires the same empirical
process as `br_density_threshold` — ideally calibrated jointly against three
labeled sample pools: (1) conventional short/medium verse, (2) long-line free
verse, (3) prose surviving the Dialogue Exclusion Guard. A provisional
default of 0.60 is proposed pending validation against a representative
corpus sample.

---

## 5. Strict Validation and Exclusion Mechanisms

### 5.1. Execution Order Optimization Clause

To maximize system throughput, the processing class implements a structural-pass triage sequence:

1. It instantiates the matcher by querying the context parameters directly.
2. It extracts the candidate block and invokes `StructuralMatcher.match()`.
3. If the structural matcher returns `"match_type": "none"`, the routine instantly breaks execution and invokes the pass-through guard clause, returning the node completely intact.
4. The global heuristic text scan is only permitted if the book manifest contains the "High Poetry Priority" flag, with the exception of explicit `<blockquote>` structures which bypass this flag constraint entirely and are always evaluated structurally.

---

## 6. DOM Mutation and Structural Output Architecture

When a block passes the geometric validation checkpoints, the orchestrator overrides the original node layout completely, restructuring its DOM tokens to align perfectly with Pandoc AST specifications.

### 6.1. Root Element Schema

The outer wrapper is modified based on its context:

* If the structural block is detected inside a `<blockquote>` element, the original `<blockquote>` tag is **strictly preserved** as the outer structural frame, and the new `<div class="poetry-block">` container wrapper is appended directly inside it.
* In all other contexts, the outer wrapper is replaced entirely by the explicit container division block:

```html
<div class="poetry-block">

```

The engine extracts metadata attributes (such as author or title) by executing an ascending tree traversal up to a maximum of 3 levels of parent nodes, or by scanning immediate collateral siblings. If found, these metadata tokens are attached as clean standard data attributes on the new division wrapper.

### 6.2. Double-Layer Line Mapping

Every individual line of verse is mapped into a strict double-layer division node to isolate block formatting from inline paragraph structures:

```html
<div class="verse-line"><p>Line content here</p></div>

```

### 6.3. Indentation Metrics

Visual indentations from the source EPUB are evaluated by a metric calculation routine that extracts inline CSS `margin-left`, `text-indent` integer values, or counts contiguous sequences of non-breaking spaces (`&nbsp;`). The calculated indent value is written as a standardized data attribute on the line wrapper:

```html
<div class="verse-line" data-verse-indent="4"><p>Indented line content</p></div>

```

### 6.4. Stanza Breaks

Consecutive runs of empty lines or pairs of `<br/><br/>` tags indicating structural transitions are transformed into a clean, empty horizontal rule separator tag:

```html
<hr class="stanza-break"/>

```

---

## 7. Object-Oriented Interface and Metadata Contract

The poetry normalizer uses an instantiable, stateful class pattern following the OOP-per-book-per-thread convention of the pipeline ecosystem.

```python
import logging
from typing import Tuple
from bs4 import BeautifulSoup
from dom_normalizer.core import BookStyleContext, PipelineStatus
from dom_normalizer.core import get_utc_timestamp, coerce_class_list

class PoetryNormalizer:
    def __init__(self, context: BookStyleContext):
        self.context = context
        self.matcher = StructuralMatcher(context)
        self.detected_poems_count = 0
        self.dialogue_blocks_excluded = 0
        self.geometric_rejections = 0

    def process(self, soup: BeautifulSoup) -> Tuple[BeautifulSoup, dict]:
        """
        Executes the isolation and token transformation of poetry structures
        over the provided DOM tree fragment.
        
        For each candidate sequence evaluated via self.matcher.match():
          - match_type != "none"                    -> mutate, increment detected_poems_count
          - rejection_reason == "dialogue_excluded"  -> increment dialogue_blocks_excluded
          - rejection_reason == "geometric_mismatch" -> increment geometric_rejections
        """
        pass
```

### 7.1. Output Metadata Contract (YAML Schema Specification)

The module guarantees that execution records are returned matching the following structured properties exactly, using canonical `PipelineStatus` values and strict ISO 8601 UTC timestamps (ending with a `"Z"` suffix via `get_utc_timestamp()`):

```yaml
poetry_processing:
  status: "success"                      # Allowed values matching PipelineStatus Enum: success, idle, error
  mode_applied: "blockquote_inspection"  # Allowed: explicit, heuristic, blockquote_inspection
  detected_poems_count: 1
  dialogue_blocks_excluded: 0             # Candidates rejected by the Dialogue Exclusion Guard (§3.4)
  geometric_rejections: 0                 # Candidates that reached separator mode but failed both
                                           # Line Density and Enjambment Ratio conditions (§4.3)
  execution_timestamp: "2026-07-08T00:25:59Z"
```
