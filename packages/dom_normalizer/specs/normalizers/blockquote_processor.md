# TECHNICAL ARCHITECTURE SPECIFICATION: `blockquote_processor` PACKAGE (Version 2.9 - FORENSIC LAYOUT ANALYSIS)

## 1. Purpose and Scope

The `blockquote_processor` is a structural reconstruction engine (Stage 2 - Block Partitioning Layer) designed to detect, extract, and unify scattered text flows into semantic XHTML `<blockquote>` elements.

* **Execution Precedence Invariant:** This module must execute strictly **after** `language_tagger` (Stage 2 core metadata initialization) and Stage 1 structural sanitization (`structural_sanitizer`), and strictly **before** any global text line-unwrapping operations. By enforcing this sequence, the processor shields specialized layouts inside a semantic parent element, preventing downstream normalization collapses.

* **Pandoc Compatibility Invariant:** Multiple paragraphs belonging to the same continuous quotation must be wrapped inside a single atomic `<blockquote>` container enclosing multiple `<p>` nodes. Downstream Pandoc parsing natively guarantees the structural integrity of multi-paragraph markdown blockquotes via this mapping.

---

## 2. Environment & Context Integration

The package operates directly over the `BeautifulSoup` tree and relies on the state populated by previous pipeline steps:

* **Per-Book Architecture Isolation:** `primary_language` is explicitly treated as a mandatory, per-book context property resolved at instantiation time (`context.primary_language`). It is strictly forbidden to treat it as a global process-level environment variable, ensuring that concurrent processing workers safely handle heterogeneous multilingual corpora.

* **The Code Shield:** Enforces `self._context.is_inside_code_block(node)` as an instance method to immediately bypass text nodes representing literal programming structures.

---

## 3. Typographical & Linguistic Search Matrices

To isolate text blocks without relying on non-standard CSS classes, the engine uses two master match groups:

### 3.1. Universal Quotation Glossary Matrix

The engine evaluates any character matching the following sets without assuming language correctness:

* **Opening / Continuation Quote Set (`OPEN_QUOTES`):** `[«,“,‹,‘,„,\",']` (Including left-pointing guillemets, directional double/single quotes, low-double quotes, single opening guillemets, and standard straight quotes). *Note: Tab characters (\t) are strictly banned from this matrix.*

* **Closing Quote Set (`CLOSE_QUOTES`):** `[»,’,”,\",']` (Including right-pointing guillemets, directional right double/single quotes, and straight quotes).

### 3.2. Sequential Segmentation Boundary Rule

If a paragraph $P_n$ satisfies a closing condition and its immediate contiguous sibling paragraph $P_{n+1}$ satisfies an opening condition, the processor **must split them into two entirely distinct `<blockquote>` containers**. It is strictly forbidden to merge consecutive independent statements.

---

## 4. The Five Pillars of Forensic Detection (Sequential Strategy Pipeline)

To resolve execution conflicts when a candidate block satisfies multiple criteria, strategies are evaluated via a **Strict Priority Cascade**. The first strategy that matches a node pattern claims it entirely, halting downstream validation for that specific node group.

```ascii
                     [Contiguous Paragraph Candidates]
                                     │
                                     ▼
                        ┌────────────────────────┐
                        │   Priority Cascade     │
                        └────────────┬───────────┘
                                     │
                ┌────────────────────┴────────────────────┐
                ▼ (Priority 1)                            ▼ (Priority 2)
      ┌───────────────────┐                     ┌───────────────────┐
      │  EpigraphStrategy │                     │PoeticQuoteStrategy│
      └─────────┬─────────┘                     └─────────┬─────────┘
                │ MATCH?                                  │ MATCH?
                ├──> YES ──> [Wrap: <blockquote           ├──> YES ──> [Wrap: <blockquote>]
                │             class="epigraph">]          │
                ▼ NO                                      ▼ NO
      ┌───────────────────┐                     ┌───────────────────┐
      │ ProseQuoteStrategy│                     │EnclosedQuotationSt│
      └─────────┬─────────┘                     └─────────┬─────────┘
                │ MATCH?                                  │ MATCH?
                ├──> YES ──> [Wrap: <blockquote>]          ├──> YES ──> [Wrap: <blockquote>
                │                                         │             + Strip Quotes]
                ▼ NO                                      ▼ NO
      ┌───────────────────┐                     ┌───────────────────┐
      │ForeignBlockStrateg│                     │ Reject Candidate  │
      └─────────┬─────────┘                     └───────────────────┘
                │ MATCH?
                ├──> YES ──> [Wrap: <blockquote>]
                ▼ NO
        [Reject Candidate]

```

### 4.1. Pillar 1: Topographic Epigraph Strategy (`EpigraphStrategy`) [Priority 1]

* **Detection Criteria:** Targets high-asymmetry, short-form introductory quotations placed at chapter boundaries.
* **Heuristic Rules:** Matches if the candidate block is located in immediate structural proximity to a valid header node (`<h1>`, `<h2>`, `<h3>`), possesses a total character length under 350 characters, and exhibits a right-aligned typographic signature (`text-align: right`).
* **DOM Mutation:** Wraps the targeted nodes inside a specialized semantic blockquote: `<blockquote class="epigraph">...</blockquote>`.

### 4.2. Pillar 2: Poetic Excerpt Statistical Strategy (`PoeticQuoteStrategy`) [Priority 2]

* **Stage 1 Structural Coexistence Invariant:** To prevent architectural conflicts with `structural_sanitizer` (which collapses `<br/>` elements inside standard paragraphs), this strategy **operates exclusively on sequences of independent sibling `<p>` blocks** (where each verse line is represented as an individual `<p>` container).
* **Known Architecture Limitation:** Unclassed poetry blocks represented via raw `<br/>` tags within a single `<p>` element (e.g., `<p>Verse 1<br/>Verse 2</p>`) are intentionally flattened during Stage 1 prior to this module's execution. This limitation is a conscious system constraint; Pillar 2 treats sibling `<p>` blocks exclusively.
* **Heuristic Rules:** Computes the mathematical mean ($\mu$) and sample variance ($\sigma^2$) of the character lengths across the sequence of sibling `<p>` elements. If the text blocks feature short lengths ($\mu \le 55$ characters) accompanied by a stable, constrained variance profile ($\sigma^2 \le 225.0$), the sequence is flagged as an embedded poem quote."
* **DOM Mutation:** Wraps the entire sequence of sibling paragraph elements inside a standard semantic `<blockquote>` container.

### 4.3. Pillar 3: Prose Structural Alignment Strategy (`ProseQuoteStrategy`) [Priority 3]

* **Detection Criteria:** Captures blocks where text indentation or margins were baked into the DOM via inline styles or volatile classes.
* **Heuristic Rules:** Matches if a paragraph or a sequence of consecutive sibling paragraphs exhibits an explicit, homogeneous `margin-left` or `padding-left` value ($\ge 1.5\text{em}$ or $\ge 20\text{px}$).
* **DOM Mutation:** Wraps the matching sequence into a standard semantic `<blockquote>` container and strips the layout-centric margin/padding variables from the internal nodes.

### 4.4. Pillar 4: Literal Typographical Enclosure Strategy (`EnclosedQuotationStrategy`) [Priority 4]

* **State Machine Rules:**

1. A sequence accumulation begins when a paragraph $P_{start}$ starts with any token in `OPEN_QUOTES` (ignoring leading whitespaces or `&nbsp;`).
2. Intermediate paragraphs $P_{start+i}$ within the same continuous flow are valid additions if they either start with an `OPEN_QUOTES` token or do not end with a `CLOSE_QUOTES` token while the next sibling continues the text flow.
3. The sequence accumulation terminates on paragraph $P_{end}$ when it ends with a character from `CLOSE_QUOTES`.

* **Text Cleansing Action:** Once bounded, the engine wraps the nodes inside a standard `<blockquote>` and runs a regex pass to strip the presentational prefix opening and suffix closing quotation marks from the boundaries of the text nodes.

### 4.5. Pillar 5: Cross-Lingual Shared Shift Strategy (`ForeignBlockStrategy`) [Priority 5]

* **Grouping Rules:** Captures contiguous text statements that share an identical foreign language context established via standard XHTML `lang` metadata attributes.

1. **Regional Subtag Normalization Rule:** Before evaluating target text shifts, the implementation **MUST** normalize the extracted `lang` attribute string by splitting it at the regional delimiter and isolating the base text code (e.g., `lang.strip().split('-')[0].lower()`). This prevents false positives where variants like `pt-BR` or `en-US` are incorrectly flagged as foreign inside a book with a base primary language of `pt` or `en` respectively.
2. Accumulation begins when a normalized paragraph code evaluates to unequal against the root environment context: `normalized_lang != BookStyleContext.primary_language`.
3. Consecutive sibling paragraphs are appended **if and only if** their normalized `lang` subtag matches the exact same foreign language token as the root of the active sequence.

* **DOM Mutation:** Wraps the sequence in a standard semantic `<blockquote>`.

---

## 5. Anti-False Positive Filter: The Text-to-Tag Ratio (`TTR`)

Before applying mutations under any strategy, the processor must pass candidate blocks through a density filter to prevent treating indices or tables of contents as citations:

$$\text{TTR} = \frac{\text{Total Words}}{\text{Total Tag Nodes} + 1}$$

If a candidate block features an explicit density profile of $\text{TTR} < 3.0$, or if anchor tags (`<a>`) constitute more than $30\%$ of the total character tokens inside the block, it is instantly blacklisted.

---

## 6. Concurrent Architecture & Strategy Pattern Blueprint

```python
from abc import ABC, abstractmethod
from typing import Tuple, List, Dict, Any
from bs4 import BeautifulSoup, Tag
from dom_normalizer.core import BookStyleContext, EngineConfiguration

class BaseBlockquoteStrategy(ABC):
    @abstractmethod
    def match(self, node: Tag, context: BookStyleContext) -> bool:
        """Determines if the structural node satisfies this specific strategy."""
        pass

class BlockquoteProcessor:
    def __init__(self, context: BookStyleContext) -> None:
        self._context = context
        self._config = context.config
        self.quotes_created_count = 0
        self.epigraphs_identified_count = 0

        # Strict Priority Cascade Architecture
        self._strategies: List[BaseBlockquoteStrategy] = [
            EpigraphStrategy(),
            PoeticQuoteStrategy(),
            ProseQuoteStrategy(),
            EnclosedQuotationStrategy(),
            ForeignBlockStrategy()
        ]

    def process(self, soup: BeautifulSoup) -> Tuple[BeautifulSoup, dict]:
        """Scans DOM tree sequentially via the localized strategy ecosystem."""
        if self.context.is_inside_code_block(soup):
            return soup, {"status": "skipped"}
        ...

```

### 6.1. Implementation Guideline: Sibling Node Traversal

To ensure type safety and prevent common static analysis errors, any strategy or helper method that traverses sibling nodes using node.find_next_sibling() must adhere to the following protocol:

The iterator variable (e.g., `current_node`) must be typed as `Optional[PageElement]` from the `bs4.element` module.
The loop must include an isinstance(`current_node`, `Tag`) check. This acts as a type guard, allowing safe access to tag-specific attributes like .name or .parent and preventing false positives from linters about unnecessary isinstance checks.

---

## 7. Output Metadata Contract (YAML)

```yaml
blockquote_processing:
  blockquotes_reconstructed: 3       
  epigraphs_isolated: 0              
  status: "success"                  # Canonical PipelineStatus: [success, success_noop, skipped, error]
  execution_timestamp: "2026-07-04T17:50:00Z"

```
