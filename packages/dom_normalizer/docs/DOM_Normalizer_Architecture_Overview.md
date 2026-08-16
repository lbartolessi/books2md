# **DOM Normalizer — Architecture Overview**

---

## 1. System Purpose

### 1.1 General Objective

**DOM Normalizer** is a high-performance, forensic engine designed to convert heterogeneous and structurally deficient HTML/XHTML/EPUB documents into a semantically uniform and predictable Document Object Model (DOM). Its primary goal is to prepare digital texts for reliable processing by downstream systems, particularly Large Language Models (LLMs) for tasks like Retrieval-Augmented Generation (RAG) and training dataset creation. The engine surgically corrects common editorial inconsistencies, conversion artifacts, and structural chaos, ensuring the output is clean, semantic, and ready for machine interpretation.

### 1.2 Problems Addressed

- **Structural Chaos:** Reconstructs semantic `<table>` structures from non-semantic `<div>` grids, and proper `<ul>`/`<ol>` lists from sequences of paragraphs that only visually resemble lists.
- **Inconsistent Editorial Patterns:** Identifies, standardizes, and relocates footnotes and endnotes using a multi-stage cascade of strategies, handling dozens of publisher-specific styles from explicit ARIA markers to forensic pattern analysis.
- **Common Conversion Artifacts:** Detects and sanitizes noise from OCR, PDF-to-HTML converters, and other automated tools, such as non-semantic page markers ("Page 123"), absolutely positioned text blocks, and dangling hyperlinks.

### 1.3 Problems Not Addressed

- **Syntactic Conversion:** The engine's scope ends at producing a clean, valid HTML DOM. It strictly forbids injecting Markdown syntax. This task is delegated entirely to a downstream tool like **Pandoc**.
- **Final Markdown Polishing:** Minor semantic issues that can only be detected _after_ Markdown conversion (e.g., de-hyphenating words split across lines, fixing paragraphs broken by stray newlines) are out of scope. This is the responsibility of a future **`md_normalizer`** tool.
- **Content Generation or Summarization:** The engine only restructures existing content; it does not alter, generate, or summarize the text itself.

### 1.4 System Guarantees

- **Idempotency:** Applying the normalization process to an already-normalized document will result in no further changes. The process is stable and repeatable.
- **Fault Tolerance & Isolation:** No single failure at the node, chapter, or processor level is allowed to crash the main orchestration pipeline. Errors result in localized, deterministic degradation, with the faulty element being skipped or passed through, and the error logged to telemetry.
- **Semantic Preservation:** The engine aims to reveal and standardize the author's original semantic intent, not alter it. It restructures markup to be more explicit but preserves the underlying content and relationships.

---

## 2. Position in the Global HTML → Markdown Pipeline

### 2.1 Complete Pipeline Overview

```text
HTML / EPUB / XHTML
        ↓
[ DOM Normalizer ]  ← (This Project)
        ↓
  Pandoc (Syntactic Conversion)
        ↓
  md_normalizer (Semantic Markdown Cleanup)
        ↓
Clean, Uniform, LLM-Friendly Markdown
```

### 2.2 Role of `dom_normalizer`

- **Preparation:** It restructures the source DOM _in-memory_ to be semantically valid and predictable. It fixes broken lists, tables, footnotes, and other structural elements before they are converted to Markdown syntax.
- **Invariants for Pandoc:** It guarantees that Pandoc receives a DOM where structural elements are represented by their correct semantic tags (e.g., `<table>`, `<ul>`, `<ol>`, `<section role="doc-endnotes">`).
- **Failure Prevention:** By cleaning the DOM, it prevents a large class of Pandoc conversion errors that arise from ambiguous or malformed HTML, leading to a more consistent and reliable output.

### 2.3 Role of Pandoc

- **Transformation:** Pandoc's role is strictly syntactic conversion. It takes the clean HTML DOM from `dom_normalizer` and translates its tags and structure into the equivalent Markdown syntax.
- **Limitations:** Pandoc is not a forensic tool. It relies on the input being well-structured. Faced with non-semantic or broken HTML, its output can be unpredictable or incorrect.

### 2.4 Role of `md_normalizer` (Future Project)

This planned downstream tool will perform the final semantic cleanup on the Markdown output itself. Its mission includes:

- Reconstructing paragraphs broken by hard line breaks.
- Removing hyphenation artifacts from words split at the end of lines.
- Standardizing quotation marks and other special characters.
- Final cleanup tasks to optimize the text for RAG chunking and dataset creation.

---

## 3. Usage Contexts

### 3.1 Book Conversion

The primary use case. It handles formats like:

- **EPUB:** The main target, with its complex internal structure of XHTML, CSS, and metadata.
- **FB2:** A format with its own native footnote semantics.
- **Publisher HTML:** Custom HTML formats from various publishing houses.
- **PDF-to-HTML:** Messy, often position-based HTML generated from PDF conversions.

### 3.2 Wikipedia Page Conversion

- **Specific Problems:** Infoboxes and navboxes that are visually tables but use complex `div` structures; deeply nested templates; inconsistent citation styles.
- **Relevant Normalizers:** `TableProcessor` and `ListProcessor` are critical.

### 3.3 Web Scraping

- **Noise Patterns:** Boilerplate content (headers, footers, ads, navigation menus), dynamic content loaded via JavaScript, non-standard tags.
- **Critical Modules:** A future `ContentExtractor` module would be key, using heuristics to isolate the main article text from surrounding noise.

---

## 4. Application Scopes

### 4.1 RAG (Retrieval-Augmented Generation)

- **Improved Chunk Quality:** By enforcing semantic boundaries, chunks are more likely to represent complete thoughts (a full paragraph, a list, a table row), reducing the chance of splitting a sentence.
- **Reduced Semantic Entropy:** Clean, structured text provides a clearer signal for embedding models, resulting in more accurate and stable vector representations.
- **Stable Embeddings:** Removing formatting noise and standardizing structure ensures that semantically identical content produces more similar embeddings.

### 4.2 Training Dataset Preparation

- **Uniform Structure:** Guarantees that all documents in the dataset share a consistent, predictable structure, which is crucial for training models to understand layout and semantics.
- **Metadata Preservation:** Preserves and standardizes important metadata (e.g., language, author), which can be used as features during training.
- **Noise Elimination:** Removes conversion artifacts and editorial inconsistencies that would otherwise be learned as noise by the model.

### 4.3 LLM-Friendly Book Formatting

- **"LLM-Friendly" Characteristics:** A document is LLM-friendly when its structure is explicit, semantic, and hierarchical. This means using `<h1>`-`<h6>` for titles, `<ul>`/`<ol>` for lists, `<table>` for tabular data, and having a clear, navigable footnote system.
- **Pipeline Contribution:** `dom_normalizer` creates this semantic structure in the DOM. `Pandoc` translates it to Markdown syntax. `md_normalizer` provides the final polish.

---

## 5. General Project Architecture

### 5.1 Module Map

```text
dom_normalizer/
├── docs/
├── prompts/
├── src/
│   └── dom_normalizer/
│       ├── __init__.py
│       ├── core.py
│       ├── utils.py
│       ├── structural/
│       │   ├── __init__.py
│       │   ├── table_processor.py
│       │   └── list_processor.py
│       ├── footnotes/
│       │   ├── __init__.py
│       │   └── footnote_processor.py
│       └── main.py  # Main DomNormalizer orchestrator class
├── tests/
├── tools/
│   └── test_suite_orchestrator.py
├── pyproject.toml
└── README.md
```

### 5.2 Conceptual Grouping

- **Core Infrastructure:** `src/dom_normalizer/core.py`, `src/dom_normalizer/utils.py`. Provides base classes, context objects (`BookStyleContext`), configuration (`EngineConfiguration`), and shared utilities.
- **Processors / Normalizers:** `src/dom_normalizer/structural/`, `src/dom_normalizer/footnotes/`. These are the specialized modules that perform the actual DOM mutations (e.g., `FootnoteProcessor`, `TableProcessor`).
- **Orchestration:** `src/dom_normalizer/main.py`. The main `DomNormalizer` class that initializes the context and runs the sequence of processors.
- **Tooling & Development:** `tools/`, `prompts/`. Contains helper scripts for development, such as the `test_suite_orchestrator.py` for generating tests with local LLMs.

### 5.3 Layer Diagram

The architecture is layered to enforce separation of concerns:

1. **Layer 1: Core Layer:** The foundation. Contains `EngineConfiguration`, `BookStyleContext`, and base strategy classes. It has no knowledge of specific processors.
2. **Layer 2: Processor Layer:** Contains the individual normalizers (`FootnoteProcessor`, etc.). Each processor depends on the Core Layer for context and configuration but is independent of other processors.
3. **Layer 3: Orchestration Layer:** The `DomNormalizer` class. It depends on the Processor and Core layers. Its job is to instantiate processors and execute them in a defined sequence on a given document.
4. **Layer 4: Application Layer:** The external script that imports and uses `DomNormalizer`. It is responsible for loading documents, creating the initial configuration, and handling the final output.

---

## 6. System's Mental Model

### 6.1 Molecular Layout Signatures

- **Representation:** A "molecular signature" is a unique combination of CSS classes, styles, and tag names that, when found together on an element, reliably indicate its semantic purpose (e.g., a `div` with classes `c1`, `c2`, and `float: left` is always a sidebar).
- **Detection:** The `BookStyleContext` parses the book's CSS at initialization to build a profile of these signatures.
- **Usage:** Processors query the context (`context.is_blockquote_element(node)`) to identify elements based on their style, even when semantic tags are absent.

### 6.2 Footnote Systems

- **Components:** A complete footnote system consists of three parts:
  - **Callouts:** The markers in the main text (e.g., `<sup><a href="#fn1">1</a></sup>`) that link to the note.
  - **Bodies:** The content of the notes themselves.
  - **Backlinks:** The links within the note bodies (e.g., `↩`) that navigate back to the callout.
- **Topology:** Refers to the physical location of note bodies, which can be in the same file as the callout or in a separate "donor file".

### 6.3 Forensic Invariants

- **Definition:** Stable, mathematical, or structural properties of a document that can be used to identify patterns when explicit semantics are missing.
- **Examples:**
  - **Prefixes:** All footnote callout IDs share a common prefix (e.g., `fnref-`).
  - **Symmetry:** A one-to-one mapping between callouts and note bodies.
  - **Cardinality:** A minimum number of occurrences for a pattern to be considered a valid system.

### 6.4 Parameterized Strategies

- **Declarative:** Defined in a simple, human-readable format (JSON) using selectors and regular expressions, not imperative code.
- **Persistent:** Stored on disk in a registry file, allowing the engine's capabilities to grow over time.
- **Reusable:** A single generic `ParameterizedFootnoteStrategy` class can handle any pattern defined in the registry.
- **No AI:** These strategies are purely deterministic and rule-based, ensuring predictable and auditable results.

---

## 7. The Normalization Cascade

The engine processes documents using a prioritized cascade of strategies. This model is most evident in the `FootnoteProcessor` but applies conceptually across the system.

### 7.1 Stage 0 — Native Convention

- **Function:** Handles formats with explicit, built-in semantics (e.g., FB2's `a[type="note"]`, EPUB3's `epub:type="footnote"`).
- **Logic:** It trusts the author's declared structure and focuses on _synthesis_ (like adding missing backlinks) rather than _detection_.

### 7.2 Stage A — Known Static Strategies

- **Function:** Applies a series of hard-coded strategies for common, well-known editorial patterns.
- **Logic:** Each strategy (`AriaDpubStrategy`, `Vellum`, `Calibre`) looks for a specific, fixed set of HTML attributes and structures. They are executed in a strict priority order.

### 7.3 Stage B — Parameterized Registry Search

- **Function:** If no static strategy matches, the engine scans a JSON registry of "forensic signatures."
- **Logic:** If a signature in the registry matches the document's structure, the engine instantiates a generic, data-driven `ParameterizedFootnoteStrategy` with the pattern's variables.

### 7.4 Stage C — Anomaly Containment

- **Function:** If no known pattern is found, this stage acts as a safety net.
- **Logic:** It sanitizes broken or inconsistent markup that lacks a clear macro-pattern, such as notes embedded directly in paragraphs (`<span>1. Note text</span>`), OCR artifacts, and dangling links.

### 7.5 Stage D — Forensic Triage (Future Capability)

- **Function:** As a last resort, this stage can be activated to mathematically analyze the document's structure.
- **Logic:** It would verify forensic invariants (prefixing, symmetry, etc.) to discover a _new_ pattern on the fly.

### 7.6 Stage E — Strategy Compilation (Future Capability)

- **Function:** Generates a new declarative strategy from the results of Stage D.
- **Logic:** It would persist the newly compiled pattern to the JSON registry for future use, allowing the system to learn from new documents.

---

## 8. Global Contracts

### 8.1 Thread Safety

The system is designed for safe parallel processing of _multiple books_. The `BookStyleContext` object is thread-isolated, containing all state for a single book. Within a single book's processing, all operations are single-threaded.

### 8.2 Pure vs. Mutating Modules

- **Pure Modules/Functions:** Analysis functions that inspect the DOM without changing it (e.g., `is_ignorable_node`, `is_page_marker_noise`, `strategy.can_process()`). They reside primarily in `core.py` or as helper methods.
- **Mutating Modules/Functions:** Processors that modify the `BeautifulSoup` object in-place (e.g., `FootnoteProcessor.process()`, `safe_convert_div_grid_to_table`).

### 8.3 Atomicity

Mutations on a single node or a small, related group of nodes should be atomic. The `safe_mutation_boundary` context manager is designed to enforce this, ensuring that if a mutation fails midway, the node is restored to its original state, preventing a corrupted DOM.

### 8.4 Idempotency

All top-level processors (`FootnoteProcessor`, `TableProcessor`) must be idempotent. Running a processor on a document it has already processed should result in no further changes. This is achieved by having processors convert structures to a canonical form and then recognizing that form on subsequent runs.

---

## 9. Extensibility

### 9.1 Adding a New Normalizer

1. **Contract:** Create a new class that inherits from a base class (e.g., `BaseStrategy`). It must implement a `can_process(soup, context)` method and a `process(soup, context)` method.
2. **Mutations:** The `process` method is allowed to mutate the `soup` object passed to it.
3. **Integration:** The new normalizer is added to the main pipeline sequence in the `DomNormalizer` orchestrator class.

### 9.2 Adding a New Parameterized Strategy

**No code changes are required.** A new entry is added to the `footnote_registry.json` file, defining the `forensic_signature` with the appropriate CSS selectors and regular expressions for the new publisher style. The existing `ParameterizedFootnoteStrategy` will automatically pick it up.

### 9.3 Adding a New Analysis Module

An analysis module should be pure (no side effects). It typically takes the `soup` and `context` as input and returns data. This data can be added to the `BookStyleContext` to be made available to other processors downstream.

---

## 10. AI Integration (for Development)

The project leverages local LLMs as a development accelerator, not a runtime dependency.

### 10.1 PR-Agent (Hypothetical)

An AI agent reviewing a Pull Request would need context on module dependencies. For example, a change in `core.py` requires careful review of all processors, while a change in `footnote_processor.py` is largely self-contained.

### 10.2 Local Models (Ollama)

The `tools/test_suite_orchestrator.py` script uses local models running via Ollama to bootstrap test cases. It feeds the AST and docstrings of a Python file to a code model, which then generates YAML-based specification and mutation tests, significantly speeding up TDD.

### 10.3 Large Models (Groq, Gemini)

Larger, more powerful models can be used for ad-hoc tasks like high-level architectural reviews, suggesting refactoring strategies, or generating complex, multi-file regression tests that simulate real-world messy documents.

---

## 11. Testing and Validation

### 11.1 Unit Tests

Each module has corresponding unit tests that validate individual functions in isolation, especially pure analysis functions.

### 11.2 Pipeline Tests

End-to-end tests that run a complete, messy document through the entire `DomNormalizer` pipeline and assert that the final DOM matches an expected clean output.

### 11.3 Invariant Tests

Tests that check for the preservation of global properties. For example, after running `FootnoteProcessor`, the total number of callouts plus orphan notes must equal the initial number of potential notes.

### 11.4 Regression Tests

A large suite of real-world EPUB and HTML files that have caused problems in the past. The entire suite is run before any release to ensure that bug fixes remain effective and that new features do not re-introduce old issues.

---

## 12. Complete Execution Example

### 12.1 Input

An EPUB chapter with two types of notes:

1. Standard notes using `<a epub:type="noteref">` pointing to `<aside epub:type="footnote">`.
2. An anomalous inline note: `<p>Some text with an inline note <small style="vertical-align: super;">2. This is an anomaly.</small></p>`.

### 12.2 Step-by-Step Pipeline

1. The `DomNormalizer` orchestrator calls `FootnoteProcessor.process(soup)`.
2. The processor iterates through its strategy cascade.
3. `NativeConventionFootnoteStrategy.can_process()` returns `False`.
4. `AriaDpubStrategy.can_process()` returns `True` because it finds `epub:type` attributes.
5. `AriaDpubStrategy.process()` is executed. It extracts the `<aside>` notes, standardizes the callouts and bodies, and rebuilds them in a canonical `<section role="doc-endnotes">` at the end of the document. The inline `<small>` tag is untouched.
6. The `DomNormalizer` orchestrator then calls `AnomalyStrategy.process(soup)` (assuming it runs after main strategies).
7. `AnomalyStrategy.can_process()` returns `True` because it finds the styled `<small>` tag that is not inside an `<a>`.
8. `AnomalyStrategy.process()` extracts the text "2. This is an anomaly.", converts it into a proper `<li>` in the existing notes section, and replaces the original `<small>` tag with a valid `<a role="doc-noteref">` pointing to the new `<li>`.

``` mermaid
sequenceDiagram
    title Sequence diagram for DOM_Normalizer in the HTML_to_Markdown_pipeline
    participant SourceHTML as Source_HTML_EPUB_XHTML
    participant DomNormalizer
    participant Pandoc
    participant MdNormalizer as md_normalizer
    participant Consumer as Downstream_LLM_System

    SourceHTML->>DomNormalizer: load_document()
    DomNormalizer->>DomNormalizer: normalize_dom()
    DomNormalizer->>Pandoc: pass_clean_dom()
    Pandoc->>Pandoc: convert_html_to_markdown()
    Pandoc->>MdNormalizer: emit_markdown()
    MdNormalizer->>MdNormalizer: cleanup_markdown_semantics()
    MdNormalizer->>Consumer: provide_clean_llm_friendly_markdown()
```

### 12.3 Output DOM

A clean XHTML document where all notes, regardless of their original format, are now part of a single `<ol>` inside a `<section class="footnotes" role="doc-endnotes">`, with full bidirectional linking.

### 12.4 Output Markdown (from Pandoc)

Pandoc would convert the clean DOM into standard Markdown with footnotes, e.g.:

```markdown
Some text with a standard note.[^1]

Some text with an inline note.[^2]

[^1]: This is a standard note.

[^2]: This is an anomaly.
```

### 12.5 Generated Telemetry

```json
{
  "footnote_processing": [
    {
      "strategy_applied": "AriaDpubStrategy",
      "processing_status": "success",
      "notes_count": 1,
      "anomalies_detected": []
    },
    {
      "strategy_applied": "AnomalyStrategy",
      "processing_status": "success",
      "notes_count": 1,
      "anomalies_detected": ["inline"]
    }
  ]
}
```

---

## 13. Glossary

- **Callout:** The marker in the main text (e.g., an `<a>` tag) that links to a footnote or endnote.
- **Body:** The content of the footnote or endnote itself.
- **Backlink:** The link from the note body back to its corresponding callout in the text.
- **Molecular Signature:** A specific combination of CSS classes, styles, and tag names used to identify an element's semantic function when standard HTML tags are absent.
- **Forensic Invariant:** A stable, mathematical, or structural property of a document's markup (e.g., all note bodies are `<div>`s with a specific class) used for pattern detection.
- **Donor File:** An HTML file within an EPUB that contains content (like all footnotes or a glossary) referenced by other files in the book.
- **Parameterized Strategy:** A processing strategy that is configured by declarative data (e.g., a JSON object with CSS selectors) rather than by hard-coded logic.
- **Structural Sanitizer:** A processor focused on fixing fundamental HTML structural issues, such as converting a grid of `<div>`s into a semantic `<table>`.

---

## 14. Project Roadmap

- **Current Status:** Core structural normalizers for tables, lists, and footnotes are implemented and robust. The foundational architecture is stable.
- **Next Modules:**
  - `BlockquoteProcessor`: For advanced blockquote and epigraph normalization.
  - `HeadingNormalizer`: To recover and standardize heading levels.
- **Future Projects:**
  - `md_normalizer`: A post-Pandoc tool for semantic cleanup of Markdown files.
- **Integration:**
  - Develop optimized tooling for RAG chunking based on the semantic boundaries identified by the normalizer.
- **Release:**
  - Plan for a public open-source release after further testing and documentation refinement.
