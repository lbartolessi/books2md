# SPECIFICATION: FORENSIC PATTERN ANALYZER AND STRUCTURAL INVARIANT EXTRACTOR (v1.0)

## 1. Scope and Target Responsibility

The `ForensicPatternAnalyzer` is a pure, non-mutating observer engine (`Pure Observer`). It runs natively during the execution of Stage 2 (Floating) and Stage 3 (Footnotes) when bundled static strategies fail to meet the confidence threshold ($\ge 0.85$).

Its sole responsibility is to apply graph-topology and statistical heuristics over the `BeautifulSoup` tree to isolate, extract, and quantify structural invariants, feeding clean data structures directly to the `DynamicStrategyCompiler`.

---

## 2. Component Architecture & Main Interface

```python
from bs4 import BeautifulSoup, Tag
from typing import Dict, Any, List, Tuple, Optional
import re
import os
from dom_normalizer.core import BookStyleContext
from structural_strategy_compiler import ForensicAnalysisError

class ForensicPatternAnalyzer:
    """
    Automated forensic engine that analyzes DOM anomalies, computes structural
    isomorphisms, and verifies bipartite graph symmetry over footnote callout
    networks. Scope is now exclusive to footnotes — floating-element detection
    was fully superseded by the Molecular Matching Engine (see
    floating_element_processor.md v2.14) and has been removed from this class.
    """
    def __init__(self, context: BookStyleContext):
        self.context = context

    def analyze_footnote_anomaly(self, soups: Dict[str, BeautifulSoup]) -> Tuple[Tag, Tag, str, str]:
        """
        Executes the 5 Invariant Bipartite Graph algorithm.
        Only reached via footnote_processor's Stage D — Stage 0/A/B/C are
        expected to have already resolved the vast majority of real books.
        """
        candidate_anchors = self._filter_and_collect_candidate_anchors(soups)
        detected_regex, structural_group = self._extract_isomorphic_href_pattern(candidate_anchors)
        topology_location, target_bodies = self._locate_topological_cluster(soups, structural_group)
        validated_pairs = self._verify_bidirectional_symmetry(structural_group, target_bodies)

        if not validated_pairs:
            raise ForensicAnalysisError("DOM Anomaly failed the Bidirectional Symmetry Invariant check.")

        sample_callout, sample_body = validated_pairs[0]
        return sample_callout, sample_body, detected_regex, topology_location

    def _extract_isomorphic_href_pattern(self, anchors: List[Tag]) -> Tuple[str, List[Tag]]:
        fragments = [a['href'].split('#')[-1] for a in anchors if '#' in a.get('href', '')]
        if not fragments:
            return "", []

        common_prefix = os.path.commonprefix(fragments)
        if len(common_prefix) >= self.context.config.min_pattern_length:
            detected_regex = f"^{common_prefix}\\d+"
        else:
            detected_regex = r"^.*$"

        # FIX: filtrar usando la expresión regular compilada real, no los
        # fragmentos de origen (que trivialmente se contienen a sí mismos)
        pattern = re.compile(detected_regex)
        structural_group = [
            a for a in anchors
            if '#' in a.get('href', '') and pattern.match(a['href'].split('#')[-1])
        ]
        return detected_regex, structural_group

    # _locate_topological_cluster, _verify_bidirectional_symmetry,
    # _filter_and_collect_candidate_anchors: sin cambios de lógica,
    # solo firma de tipo actualizada a BookStyleContext donde aplique.
```

---

## 3. Detailed Footnote Forensic Algorithm (The 5 Invariant Pipeline)

The internal procedural steps for `analyze_footnote_anomaly` execute using strict deterministic graph rules:

### 3.1. Stage 1: Candidate Filtering and Sieve

The engine scans all `<a>` tags across the document. An anchor is structurally discarded from the footnote track if it meets any of the following parameters:

* The `href` is external (starts with `http://` or `https://`).
* The destination ID points directly to a heading tag (`<h1>`, `<h2>`, `<h3>`), which mathematically flags it as a standard **Table of Contents (TOC)** entry.
* The anchor has no local `id` attribute or immediate parent `id` container within 2 text-nodes of distance (Violates **Invariant 1 & 2**).

### 3.2. Stage 2: Isomorphic Lexical Extraction (Calculating `detected_regex`)

To find the common pattern of the footnotes without hardcoded guesses, the engine extracts the fragment strings (the part after the `#` in the `href`) of all remaining candidates and computes their **Common Longest Prefix/Suffix Structure**:

### 3.3. Stage 3: Topological Contiguity Check (Locating the Cluster)

Using the destinations of the `structural_group`, the engine resolves their target elements in the DOM tree. It then calculates their density:

* If $\ge 80\%$ of the targets reside inside the same separate file (e.g., `notes.xhtml`), `topology_location` is marked as `"donor_file"`.
* If the targets are appended at the bottom of individual chapters as adjacent siblings sharing the same parent container (`<div>`, `<section>`), `topology_location` is marked as `"end_of_section"`.

### 3.4. Stage 4: Verification of Bidirectional Symmetry (The Back-link Invariant)

This is the mathematical core. For every candidate pair (Callout $\rightarrow$ Target Body), the engine inspects the inner DOM of the Target Body:

```python
def _verify_bidirectional_symmetry(self, callouts: List[Tag], bodies: List[Tag]) -> List[Tuple[Tag, Tag]]:
    validated_pairs = []
    for callout in callouts:
        callout_id = callout.get('id')
        target_href_fragment = callout['href'].split('#')[-1]
        
        # Locate the body asset matching this fragment
        for body in bodies:
            if body.get('id') == target_href_fragment:
                # INVARIANT 5: Search for an internal back-link pointing exactly to callout_id
                back_links = body.find_all('a', href=True)
                for bl in back_links:
                    bl_fragment = bl['href'].split('#')[-1]
                    if bl_fragment == callout_id:
                        validated_pairs.append((callout, body))
                        break
    return validated_pairs

```

If the list of `validated_pairs` is empty or its size represents less than 50% of the total cluster, the engine aborts execution, classifying the structure as standard cross-references instead of a footnote system.

