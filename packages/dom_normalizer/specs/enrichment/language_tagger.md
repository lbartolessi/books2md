# TECHNICAL ARCHITECTURE SPECIFICATION: `language_tagger` PACKAGE (Version 2.3 - DYNAMIC CALIBRATION CORE)

## 1. Purpose and Scope

The `language_tagger` package provides an in-memory DOM transformation layer using `BeautifulSoup` to detect, validate, and recursively tag variations and context shifts in natural language across structural and inline elements.

- **Execution Stage:** This module runs within **Stage 2 (Semantic Micro-Normalizers)**.
- **Core Objective:** Ensure that any text node or phrase segment containing text in a language that diverges from its immediate cascading context is explicitly marked using standardized XHTML attributes to guarantee universal accessibility and perfect text-to-speech (TTS) synthesis engine performance.
- **Strict Invariants:**
  1. **The Code Shield:** This module strictly complies with the global exclusion protocol (`core.inside_code_block`). Text inside `<pre>` or `<code>` blocks must never be evaluated, altered, or tagged.
  2. **Lexical Boundary Limitation:** The insertion of automated language tags (`<span>`) must limit its scope exclusively to raw text content with real semantic value. It is strictly forbidden to wrap leading or trailing whitespaces, tabs, or orphan punctuation marks, preventing erratic pauses or intonation glitches in screen readers.

---

## 2. Runtime Environment & Engine Integration

The package handles local inference using the `lingua` high-performance implementation (backed by Rust compiled state transductors via PyO3). It resolves its operational constraints directly from the consolidated context object:

- **`context.primary_language`**: `ISOLanguageCode` instance (immutable, validated
  ISO 639-1 code) exposed directly by `BookStyleContext`, defining the fallback
  baseline language declared in the EPUB manifest metadata.
- **`context.config.lingua_low_memory_mode`**: Boolean flag on `EngineConfiguration`
  ensuring the plugin loads optimized data models under constrained environments.

---

## 3. Mathematical Model: Dynamic Thresholding & Quality Indicator ($Q$)

To counteract the statistical entropy explosion that occurs when analyzing short text strings, this package replaces all legacy static word counts with an **Exponential Decay Dynamic Threshold Model** linked to a normalized **Unique Quality Indicator ($Q$)**.

### 3.1. Exponential Decay Model

The maximum probability threshold required to validate a language prediction ($MP_{threshold}$) decreases as a function of the text length measured in words ($w_n$):

$$MP_{threshold}(w_n) = MP_{MIN} + (MP_{MAX} - MP_{MIN}) \cdot e^{-k \cdot (w_n - 1)}$$

Where the system constants are calibrated under the strict "zero false positives" directive:

- **$MP_{MAX} = 1.0$**: Absolute certainty threshold enforced for single isolated words ($w_n = 1$) to neutralize interlinguistic homographs and names.
- **$MP_{MIN} = 0.85$**: Asymptotic minimum security threshold allowed for very long fragments where statistical convergence is robust.
- **$k \approx 0.13165$**: Exponential decay velocity coefficient, derived mathematically to enforce a precise target threshold of $0.88$ at exactly ten words ($w_n = 10$).

### 3.2. Unique Quality Indicator Formula ($Q$)

To optimize runtime lookups and eliminate chained conditionals, the engine evaluates the classification using a single dimensionless quality coefficient $Q$:

$$Q = \frac{\text{Confidence}(Language_{Detected})}{MP_{threshold}(w_n)}$$

### 3.3. Binary Decision Rule

- **If $Q \ge 1.0$**: The prediction is statistically safe. The language shift is accepted, and the text boundaries are wrapped.
- **If $Q < 1.0$**: The prediction fails the dynamic security constraint. The text fragment is assumed to match the baseline cascading context or is treated as an unclassifiable token. **No tag is written**, neutralizing false positives.

---

## 4. The Recursive Cascade Machine & Structural Rules

The module processes the DOM via a **Top-Down Recursive State Inheritance** model.

1. **State Initialization:** The tracking variable `current_context_lang` is set to `EngineConfiguration.primary_language`.
2. **Downward Traversal:** For every sub-node:
   - If a valid `lang` attribute exists on the tag, `current_context_lang` updates locally for that branch.
   - If no attribute is found, it inherits its parent's active state.
3. **Attribute Serialization Order:** When inserting or mutating tags, the script must ensure that the `lang` attribute strictly precedes the `xml:lang` attribute in the element's declaration sequence (`<span lang="en" xml:lang="en">`), satisfying the formatting syntax required by the _Standard Ebooks Manual of Style_.

---

## 5. Algorithmic Implementation Template

```python
import math
from datetime import datetime, timezone
from typing import Tuple, List
from bs4 import BeautifulSoup, Tag, NavigableString
from dom_normalizer.core import BookStyleContext, PipelineStatus
from dom_normalizer.core import get_utc_timestamp
from lingua import LanguageDetectorBuilder, Language

class LanguageTagger:
    """
    Implements recursive top-down context language tagging with an
    exponential-decay dynamic confidence threshold.
    """
    def __init__(self, context: BookStyleContext):
        self.context = context
        # CORRECTED: k derived from solving threshold(10) = 0.88 exactly
        self.MP_MAX = 1.0
        self.MP_MIN = 0.85
        self.k = 0.17883  # was 0.13165 — verified: gives threshold(10) ≈ 0.8800

        languages = [Language.SPANISH, Language.ENGLISH, Language.FRENCH,
                     Language.ITALIAN, Language.PORTUGUESE, Language.LATIN]
        builder = LanguageDetectorBuilder.from_languages(*languages)
        if self.context.config.lingua_low_memory_mode:
            builder.with_low_accuracy_mode()
        self.detector = builder.build()
        self.shifts_tagged_count = 0
        self.nodes_evaluated_count = 0

    def calculate_dynamic_threshold(self, word_count: int) -> float:
        if word_count < 1:
            return 1.0
        return self.MP_MIN + (self.MP_MAX - self.MP_MIN) * math.exp(-self.k * (word_count - 1))

    def process(self, soup: BeautifulSoup) -> Tuple[BeautifulSoup, dict]:
        base_lang = str(self.context.primary_language)
        self._traverse_node(soup, base_lang)
        metadata = {
            "language_tagging": {
                "primary_context_language": base_lang,
                "nodes_evaluated": self.nodes_evaluated_count,
                "contextual_shifts_tagged": self.shifts_tagged_count,
                "status": PipelineStatus.SUCCESS.value if self.shifts_tagged_count > 0 else PipelineStatus.IDLE.value,
                "execution_timestamp": get_utc_timestamp()
            }
        }
        return soup, metadata

    def _traverse_node(self, node: Tag, current_context_lang: str):
        if self.context.is_inside_code_block(node):
            return

        if node.has_attr('lang'):
            current_context_lang = node['lang'].lower()

        # Target child text nodes safely avoiding presentation wrappers
        children = list(node.children)
        for child in children:
            if isinstance(child, NavigableString):
                raw_text = str(child)
                stripped_text = raw_text.strip()
                words = stripped_text.split()
                word_count = len(words)

                if word_count >= 1:
                    self.nodes_evaluated_count += 1
                    # Execute Lingua Confidence Evaluation
                    conf_values = self.detector.compute_language_confidence_values(stripped_text)
                    if not conf_values:
                        continue

                    top_prediction = conf_values[0]
                    detected_lang = top_prediction.language.iso_code_639_1.name.lower()
                    confidence = top_prediction.value

                    if detected_lang != current_context_lang:
                        threshold = self.calculate_dynamic_threshold(word_count)
                        Q = confidence / threshold

                        if Q >= 1.0:
                            # Safe detection confirmed: Mutation layer triggered
                            self._mutate_text_node(child, node, detected_lang, words)
            elif isinstance(child, Tag):
                self._traverse_node(child, current_context_lang)

    def _mutate_text_node(self, child: NavigableString, parent: Tag, lang: str, words: List[str]):
        """
        In-place DOM text mutation isolating spaces and enforcing Standard Ebooks layout properties.
        """
        # [Implementation logic for strict lexical boundary matching]
        # Generates: <span lang="en" xml:lang="en">foreign-text</span>
        # Ensures attribute 'lang' structurally precedes 'xml:lang'
        self.shifts_tagged_count += 1

```

---

## 6. Output Metadata Contract (YAML)

```yaml
language_tagging:
  primary_context_language: "es" # Baseline inherited fallback configuration string
  nodes_evaluated: 142 # Total count of individual NavigableString blocks evaluated
  contextual_shifts_tagged: 8 # Total safe structural shifts isolated and wrapped under Q >= 1.0
  status: "success" # Canonical PipelineStatus: [success, idle, error]
  execution_timestamp: "2026-06-29T18:15:00Z" # Dynamic runtime compliance timestamp
```
