# Poetry and Line-Block Normalization: Heuristic and Structural Specification

This document provides a fine-grained technical specification for the heuristic-based identification and normalization of poetry and other `line-block` structures within semantically poor or corrupt HTML/XHTML documents.

## 1. Architectural Objective

The primary goal is to reliably identify text blocks that are intentionally formatted with hard line breaks, regardless of their semantic content (e.g., poetry, laundry lists, dialogue). The system will be architected to perform this identification by analyzing the structural and topological properties of the DOM, moving away from unreliable semantic clues like CSS class names.

The canonical output for any identified structure will be a single `<div class="line-block">` container, with individual lines of text separated by `<br />` tags. This format is the required input for Pandoc to correctly generate Markdown line blocks (`|`).

## 2. Part 1: The Unified Detection Strategy

A multi-layered "defense-in-depth" heuristic function, `is_line_block_structure(tag)`, will be implemented to identify candidate containers. This function will evaluate nodes against a series of structural patterns in order of reliability.

### Level 1: Semantic Standard (Gold Standard)

* **Rule:** A tag is a candidate if it possesses the attribute `epub:type="z3998:poem"`.
* **Rationale:** This is the most reliable but rarest indicator, conforming to the DAISY/EPUB 3 standard. It should be checked first to provide an immediate, high-confidence match.

```python
def is_line_block_structure(tag):
    # Level 1: The Gold Standard
    if tag.get('epub:type') == 'z3998:poem':
        return True
    # ... more levels
```

### Level 2: Structural Heuristic (Explicit Line Breaks)

* **Rule:** A `<p>`, `<div>`, or `<blockquote>` tag is a candidate if it contains **two or more direct** `<br />` child tags.
* **Rationale:** Prose paragraphs rarely contain multiple explicit line breaks. This pattern is a strong indicator of manually formatted verse, commonly found in documents converted by tools like Calibre. The `recursive=False` constraint is crucial to avoid matching paragraphs that simply contain a single block with internal breaks.

```python
def is_line_block_structure(tag):
    # ...
    # Level 2: BR Density Heuristic
    if tag.name in ['p', 'div', 'blockquote']:
        direct_br_tags = len(tag.find_all('br', recursive=False))
        if direct_br_tags >= 2:
            return True
    # ... more levels
```

### Level 3: Structural Heuristic (Single-Column Table)

* **Rule:** A `<table>` tag is a candidate if it contains more than one `<tr>` and **every `<tr>`** within it contains exactly one `<td>` and zero `<th>` elements.
* **Rationale:** This "duck typing" rule identifies tables used for layout alignment rather than data presentation. This pattern is a known fingerprint of older digital archives (e.g., Library of America) for formatting poetry.

```python
def is_line_block_structure(tag):
    # ...
    # Level 3: Single-Column Table Heuristic
    if tag.name == 'table':
        rows = tag.find_all('tr', recursive=False)
        if not rows:
            tbody = tag.find('tbody')
            if tbody:
                rows = tbody.find_all('tr', recursive=False)

        if len(rows) > 1:
            is_single_column_table = all(
                len(row.find_all('td', recursive=False)) == 1 and
                not row.find_all('th', recursive=False)
                for row in rows
            )
            if is_single_column_table:
                return True

    return False
```

## 3. Part 2: The Sibling Cluster Consolidation Strategy

To address "fragmented blocks" where each verse is a separate `<p>` tag, a pre-processing pass, `consolidate_fragmented_line_blocks`, will traverse the DOM and merge these sequences.

### Rule A: Sequence Trigger

* A sequence is initiated when **three or more** consecutive sibling nodes of type `<p>` or `<div>` are found.

### Rule B: Length Constraint

* Every node within the candidate sequence must have a stripped text length of **85 characters or fewer**. This threshold prevents the accidental consolidation of standard prose paragraphs.

### Rule C: Dialogue Exclusion Filter

* A sequence is immediately broken and processed if any node within it begins with a common dialogue marker. This is a critical guard against false positives in conversational text.
* **Pattern:** `^\s*(—|–|-|«|"|'|„)`

### Transformation Logic

1. When a valid sequence is identified, a new `<div class="line-block">` wrapper is created and inserted into the DOM immediately before the first node of the sequence.
2. Each node from the sequence is moved inside this new wrapper.
3. A `<br />` tag is appended to the content of each moved node.
4. The original node tag (e.g., `<p>`) is dissolved using `unwrap()`, leaving only its text content and the newly appended `<br />` tag inside the `line-block` wrapper.

## 4. Part 3: DOM Transformation for Pandoc Canonical Form

Regardless of the detection heuristic used, any container identified as a line-block structure must undergo two mandatory mutations to ensure clean Pandoc conversion.

1. **Tag Transmutation:** The tag's name must be programmatically changed to `div`. This prevents Pandoc from applying unwanted formatting, such as rendering a `<blockquote>` as a Markdown quote (`>`).
    * **Implementation:** `tag.name = 'div'`

2. **Class Normalization:** The tag's `class` attribute must be completely overwritten to `['line-block']`. This removes all original (and potentially corrupt or irrelevant) classes and provides Pandoc with the exact selector it requires.
    * **Implementation:** `tag['class'] = 'line-block'`

## 5. Implementation Plan

These heuristics will be integrated into the existing `poetry` module.

1. **New Pre-processing Step:** The `consolidate_fragmented_line_blocks` function will be called early within the `PoetryNormalizer.process` method. It will run on the main `soup` object *before* the `_collect_candidates` loop. This ensures that fragmented blocks are fused into single `div.line-block` candidates that can be correctly handled later.

2. **New Heuristic Strategy:** A new strategy class, `HeuristicLineBlockStrategy`, will be created. Its `can_process` method will be a direct implementation of the `is_line_block_structure` function. This strategy will be added to the `StructuralMatcher` to run as a fallback after the `ParameterizedPoetryStrategy`.

3. **Refinement of `HeuristicSeparatorStrategy`:** The existing `HeuristicSeparatorStrategy` is based on more complex text metrics (enjambment, density). The new, simpler structural heuristics should be prioritized. The `HeuristicSeparatorStrategy` can be kept as a final, more computationally expensive fallback for cases that escape the structural net.

4. **Future Work (`PoetryStrategyCompiler`):** The patterns successfully identified by these heuristics can serve as training data for a future `PoetryStrategyCompiler`. Such a compiler could analyze the attributes of a heuristically-matched block and auto-generate a new, high-confidence entry for the `structural_registry.json`, thus allowing the system to "learn" new patterns over time.

---
