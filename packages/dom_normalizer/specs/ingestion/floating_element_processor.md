# SPECIFICATION: `floating_element_processor` PACKAGE (Version 2.14 - ZERO-CLASS ANNIHILATION CONTRACT)

## 1. Architectural Purpose and Scope

The `floating_element_processor` acts as an isolation barrier within the ingestion pipeline. Its primary function is to intercept non-linear layout components—such as sidebars, marginal notes, floating callouts, and secondary text boxes—and mutate them into semantic `<aside>` structures. This ensures downstream tokenizers and semantic slicing tools used in Retrieval-Augmented Generation (RAG) models do not suffer from narrative line contamination or token duplication.

### Pipeline Order and Dependency Contract

This module operates under a strict positional constraint:

* **Execution Sequence:** It runs **third and last** within Stage 1.
* **Upstream Dependencies:** It executes exclusively after `structural_sanitizer` and `navigation_purger` have finalized their mutations.
* **Class Promotion Guarantee:** It relies on the absolute guarantee that `structural_sanitizer` has swept the document and promoted raw, inline CSS styles (e.g., `style="float: left;"`) to the canonical `floating-element` class. The identity verification engine of this processor inspects tokenized class arrays exclusively; it must never read raw HTML `style` attributes directly.

---

## 2. Class Interface & Internal State Contract

Every implementation of the processor must expose a deterministic interface and maintain precise telemetry counters to support execution tracking and verification:

```python
from bs4 import BeautifulSoup
from dom_normalizer.core import BookStyleContext

class FloatingElementProcessor:
    def __init__(self, context: BookStyleContext, soup: BeautifulSoup) -> None:
        """
        Initializes the semantic isolation engine.
        
        Args:
            context: core class managing style heuristics and global configurations.
            soup: The complete BeautifulSoup document tree for text length caching.
        """
        self.context: BookStyleContext = context
        
        # Telemetry and Validation Counters
        self.asides_created: int = 0
        self.dense_nodes_preserved: int = 0
        self.elements_evaluated: int = 0
        
        # Performance Cache Token
        self._total_document_chars: int = 0

```

---

## 3. Context Optimization Caching (O(n²) Prevention)

To preserve a strict linear computational footprint (O(n)) across massive book documents, the processor must avoid repetitive DOM tree traversals during execution.

* **Initialization Lifecycle:** During `__init__`, the processor must invoke `soup.get_text()` exactly once.

* **Storage:** The character count of this text extraction must be stored as an integer inside `self._total_document_chars`.

* **Loop Execution Rule:** Under no circumstances should `.get_text()` or recursive structural searches be performed on the root `soup` object inside the processing loop. All density subroutines must evaluate candidates by querying this static cached integer.

---

## 4. The 5-Step Operational Guard Framework

The core engine iterates through the document's elements and subjects each candidate node to HTML verification gates:

### Step 1: Code Block Shield

* **Logic:** Evaluate if the candidate node resides inside a preformatted code block or technical environment.

* **Condition:** Call `self.context.is_inside_code_block(node)`. If it returns `True`, immediately abort evaluation and advance to the next element.

### Step 2: Molecular Identity Verification

* **Logic:** Query the global context to check if the element matches targeted layout styles or specific structural classes.

* **Condition:** Call `self.context.is_floating_element(node)`. If `False`, skip the element entirely. If `True`, increment the metric tracker `self.elements_evaluated` by 1 and advance to Step 3.

### Step 3: Containment Guard

* **Logic:** Protect the macro narrative architecture from accidental extraction.

* **Condition:** Inspect the internal subtree of the candidate node. If it contains any major structural tag (`<body>`, `<main>`, `<article>`) or harbors more than one heading tag (`<h1>`, `<h2>`, `<h3>`), it must be treated as primary content.

* **Action:** Abort processing for this node, increment `self.dense_nodes_preserved` by 1, and preserve the node intact within the tree.

### Step 4: Absolute Length Exemption & Density Cap Allocation

* **Absolute Length Exemption:** Calculate the specific character length of the node's inner text:
**node_chars = len(node.get_text())**
To prevent short, legitimate margin comments or unit-test HTML snippets from being starved by relative ratio calculations, any node where **node_chars < 50** is **exempted** from density verification and approved for immediate mutation.

* **Dynamic Cap Allocation:** For nodes containing 50 characters or more, determine the allowed Character Density Ratio (CDR) limit based on visual properties:

* *Layout Enhanced Cap:* If the node features clear structural layout presentation metadata (e.g., attributes like `data-meta-layout="true"`, background declarations like `data-orig-bg`, or explicit layout indicators like `sidebar` in its classes), set the maximum allowable threshold to **0.65** (65%).

* *Standard Cap:* If the node matches identity checks but contains no layout metadata or explicit presentation containers, set the restrictive baseline threshold to **0.20** (20%).

### Step 5: Length Cap Threshold Validation

* **Logic:** Evaluate the relative density of non-exempt candidate nodes against the total document space.

* **Formula:** Compute the active ratio as:
**CDR = node_chars / self._total_document_chars**

* **Evaluation:**
* If **CDR > threshold**, the node is deemed too dense to represent auxiliary content. Treat it as primary content: increment `self.dense_nodes_preserved` by 1 and preserve it intact.

* If **CDR <= threshold**, approve the node for semantic transformation.

---

## 5. Transformation Action & Node Reconstruction

Once a node successfully clears all five operational guards, it undergoes an in-place structural mutation:

1. **Tag Creation:** Instantiated as a new, clean semantic `<aside>` element within the active document tree.

2. **Strict Attribute Stripping (Zero-Class Policy):** To comply with pipeline normalization and strict isolation tests, the processor **MUST** strip all original classes, inline styles, and presentation attributes from the node.

* The newly created `<aside>` tag **MUST NOT** have a `class` attribute under any circumstance.
* It must **exclusively retain the `id` attribute** (if present) to preserve deep-linking capabilities.

1. **Content Migration:** Transfer all children and internal nodes from the source element into the new `<aside>` container, maintaining their exact sequence and integrity.

2. **DOM Substitution:** Replace the original element in the DOM tree with the newly constructed `<aside>` structure, and increment `self.asides_created` by 1.

---

## 6. MANDATORY NEGATIVE CONSTRAINTS (ANTI-HALLUCINATION GUARDRAILS)

To prevent code generation models from over-engineering the implementation based on patterns from other modules, the following restrictions are absolute laws:

* **PROHIBITION OF CLASS INJECTION:** The implementation **MUST NOT** inject the historical class `"floating-box"`, `"floating-element"`, or any other arbitrary string into the `class` attribute of the mutated `<aside>` tag.

* **PROHIBITION OF SHARED CLASS UTILITIES:** The implementation **SHALL NOT** import or utilize `coerce_class_list` or any other list-unification helper inside this module. Since the target tag cannot possess classes, any attempt to parse or format class arrays is an architectural violation.
* **PROHIBITION OF ATTRIBUTE COPYING:** The implementation **MUST NOT** use loops or bulk-copy methods (like `node.attrs.copy()`) to clone metadata to the new tag. Attributes must be audited individually, copying exclusively the `id`.

---

## 7. Canonical Metadata Contract (YAML)

Upon completing its execution pass, the `process()` method must compile and return an execution log dictionary matching this explicit key structure:

```yaml
floating_element_processing:
  asides_created: int
  dense_nodes_preserved: int
  elements_evaluated: int
  status: "success" | "error"
  execution_timestamp: "YYYY-MM-DDTHH:MM:SSZ"

```
