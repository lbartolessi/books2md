# TECHNICAL ARCHITECTURE SPECIFICATION: `footnote_processor` PACKAGE (Version 2.3 - PARAMETERIZED CORE)

## 1. Purpose and Scope

This package operates strictly as an in-memory DOM manipulation layer on `BeautifulSoup` objects. Its sole responsibility is to reorder, isolate, type, and standardize the hierarchical tree of footnotes and endnotes across multi-chapter EPUB resources using static or data-parameterized strategies.

- **Absolute Data Invariant:** Generating or injecting raw Markdown syntax, string markers, or physical Pandoc tags (like `:::`, `[^1]`, or `|`) is strictly forbidden. All structural mutations must be executed exclusively by altering native `BeautifulSoup` nodes and attributes, ensuring the tree remains fully valid downstream.

---

## 2. Runtime Environment Configuration

The package dynamically resolves persistence paths through the formalized properties natively integrated into the central configuration object (`EngineConfiguration`):

- **`EngineConfiguration.footnote_registry_path`:** Absolute path to the persistent JSON file for the registry of normalized notes and learned forensic signatures.
- **`EngineConfiguration.floating_registry_path`:** Absolute path to the JSON file for the registry of non-linear box layouts.

---

## 3. Interfaces, Registry Schema, and Flow Cascade

### 3.1. Contract Interface (`BaseFootnoteStrategy`)

Abstract base class that establishes the imperative contract for all footnote extraction and relocation strategies:

```python
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from core.context import BookStyleContext
from typing import Tuple

class BaseFootnoteStrategy(ABC):
    """Abstract base class that defines the structural mutation contract for all note processing strategies."""
    @abstractmethod
    def can_process(self, soup: BeautifulSoup, context: BookStyleContext) -> bool:
        """Evaluates if the DOM resource contains elements that match the note signature."""
        pass

    @abstractmethod
    def process(self, soup: BeautifulSoup, context: BookStyleContext) -> Tuple[BeautifulSoup, dict]:
        """Executes the in-place mutation on the DOM and returns the mutated soup along with its metadata."""
        pass

```

### 3.2. Esquema del Registro (`footnote_registry.json`)

Stores forensic signatures indexed by a pure mathematical content hash, ensuring the global uniqueness of the pattern regardless of the document where it is discovered:

```json
{
  "registered_patterns": [
    {
      "pattern_id": "param_fn_a4b2c1d9",
      "forensic_signature": {
        "callout_regex": "^fnref-[a-f0-9]+",
        "body_topology_location": "donor_file",
        "body_selector": "div.loa-annotation-block",
        "backlink_selector": "a.backlink-return",
        "requires_context_extraction": true
      }
    }
  ]
}
```

### 3.3. Cascada de Prioridad de Ejecución (Compuertas de Flujo)

- **Stage 0 (Native Format Convention — Synthesis, not Detection):** Activado
  cuando el orquestador suministra `native_notes_location: Optional[str]`
  al construir `FootnoteProcessor` — ya resuelto por el propio
  `BaseBookLoader` del orquestador (ver `book_loader.md`). Este módulo no
  importa ni conoce `BaseBookLoader`.
  1. Instancia `NativeConventionFootnoteStrategy` con el `file_key` devuelto
     por `get_native_notes_location()`.
  2. Para cada llamada (`<a type="note" xlink:href="#target_id">`), genera
     un identificador de retorno único: `fnref-{target_id}-{sequential_index}`.
  3. Inyecta un backlink `role="doc-backlink"` en el nodo de la nota
     correspondiente, apuntando al identificador de retorno recién creado.
  4. Nunca marca `ForensicAnalysisError`; si el enlace de ida no resuelve
     (id roto en el propio XML fuente), el par se omite y se registra en
     telemetría, pero no aborta el procesamiento del resto del libro.

- **Stage A (Known Static Strategies):** Attempts to match the DOM with standard
  editorial structures, evaluated in strict priority order:

  `AriaDpubStrategy` → `Default` → `Secular` → `InDesign` → `Calibre` → `Vellum` → `Generic`
  - **`AriaDpubStrategy` (Highest Priority):** Detects explicit DPUB-ARIA / EPUB3
    semantic markers — `epub:type="footnote"`, `epub:type="noteref"`,
    `role="doc-footnote"`, `role="doc-noteref"`, `role="doc-backlink"` — on
    callout anchors or body containers. Since this is the author's own explicit
    semantic declaration rather than a heuristic inference about publisher
    tooling, it takes absolute precedence over every other Stage A strategy.
    This strategy is the exclusive owner of ARIA/DPUB footnote vocabulary
    across the entire pipeline; no other module inspects `doc-footnote` or
    `doc-noteref` roles.

- **Stage B (Parametric Registry Search):** If static strategies return `can_process() == False`, it scans `footnote_registry.json`. If it finds an exact signature match, it instantiates the native `ParameterizedFootnoteStrategy` class with its declarative variables.
- **Stage C (Anomaly Containment Strategy - `AnomalyStrategy`):** If no parametric signatures are registered, this module intervenes to isolate and sanitize broken or inconsistent markup that lacks macro-structural patterns:

1. _`inline`:_ Captures notes illegally embedded in the middle of paragraphs (`<span>` or `<small>` with superscript styles but no links).
2. _`flat-text`:_ Resolves notes written as plain text at the end of the section without `href` anchors or return IDs.
3. _`ocr`:_ Normalizes blocks broken by old OCR software that have absolute positional attributes (`style="position:absolute"`).
4. _`dangling-refs`:_ Sanitizes callouts whose links point to non-existent ID fragments within the global EPUB container.

- **Stage D (Forensic Triage):** Activated solely and strictly **when all previous stages fail to contain the resource**. It invokes `StructuralStrategyCompiler.compile_footnote_strategy()` to analyze the algebraic invariants of the bipartite callout graph, atomically persist the new JSON signature, and apply the mutation on the fly.

---

## 4. Contrato de la Estrategia Parametrizada

The `ParameterizedFootnoteStrategy` class completely eliminates probabilistic runtime code generation by mapping forensic variables directly to native DOM manipulation loops:

```python
from datetime import datetime, timezone
from typing import Dict, Any, Tuple
from bs4 import BeautifulSoup
from core.context import BookStyleContext
from processors.footnotes import BaseFootnoteStrategy

class ParameterizedFootnoteStrategy(BaseFootnoteStrategy):
    """Unified operational strategy guided by declarative metadata. Maps persisted forensic variables to deterministic BeautifulSoup transformations."""
    def __init__(self, config_params: Dict[str, Any]):
        self.config = config_params
        signature = config_params["forensic_signature"]
        self.callout_regex = signature["callout_regex"]
        self.body_selector = signature["body_selector"]
        self.backlink_selector = signature.get("backlink_selector", "a")
        self.topology_location = signature["body_topology_location"]

    def can_process(self, soup: BeautifulSoup, context: BookStyleContext) -> bool:
        """Evaluates if the parameterized structural selectors exist in the current DOM."""
        return bool(soup.select(self.body_selector))

    def process(self, soup: BeautifulSoup, context: BookStyleContext) -> Tuple[BeautifulSoup, dict]:
        """Executes in-place mutations by applying node isolation."""
        # [Native implementation of element movement, unlinking, and typing]

        metadata = {
            "footnote_processing": {
                "strategy_applied": f"ParameterizedFootnoteStrategy:{self.config['pattern_id']}",
                PipelineStatus.SUCCESS.value,
                "anomalies_detected": [],
                "notes_count": len(soup.select(self.body_selector)),
                "execution_timestamp": get_utc_timestamp()
            }
        }
        return soup, metadata

```

```python
class NativeConventionFootnoteStrategy(BaseFootnoteStrategy):
    """
    Synthesizes the reverse link for formats whose specification declares
    forward-only note references (FB2's type="note"/xlink:href) or
    unambiguous semantic markers (EPUB3 DPUB-ARIA). Trusts the forward
    link by construction — performs no forensic verification.
    """
    def __init__(self, notes_file_key: str) -> None:
        self.notes_file_key = notes_file_key
        self.unresolved_targets: List[str] = []

    def can_process(self, soup: BeautifulSoup, context: BookStyleContext) -> bool:
        return bool(soup.select('a[type="note"]'))

    def process(self, soup: BeautifulSoup, context: BookStyleContext) -> Tuple[BeautifulSoup, dict]:
        # [Implementación: recorrer <a type="note">, generar fnref-{target}-{n},
        #  localizar la sección destino en notes_file_key, inyectar backlink
        #  role="doc-backlink" apuntando al fnref sintetizado]
        metadata = {
            "footnote_processing": {
                "strategy_applied": "NativeConventionFootnoteStrategy",
                PipelineStatus.SUCCESS.value,
                "anomalies_detected": [],
                "notes_count": 0,   # placeholder
                "unresolved_targets": self.unresolved_targets,
                "execution_timestamp": get_utc_timestamp()
            }
        }
        return soup, metadata
```

---

## 5. Invariantes Operativas Centrales y Lógica de Donantes

### 5.1. Algoritmo Estricto de Clasificación de Archivos Donantes

An HTML resource within the EPUB is classified as an _Exclusive Note Donor_ (`is_donor_file`) if and only if it simultaneously meets the following heuristic rules:

1. **Inbound References:** It receives external linked references (`href` anchors from other files pointing to its internal IDs).
2. **Absence of Narrative Flow:** It has a total absence of standard narrative flow (zero `<p>` or `<div>` blocks containing free text outside of the note structures).

### 5.2. Notas Anidadas en Elementos Flotantes

Al recorrer los ancestros de una llamada, si se encuentra un `<aside>`:

1. Si el `<aside>` tiene `id` nativo (preservado por la Zero-Class Policy
   de `floating_element_processor`), se usa directamente como ancla de
   retorno.
2. Si no tiene `id`, `footnote_processor` le inyecta un UUID corto sobre
   la marcha — sin requerir ningún cambio en `floating_element_processor`,
   que permanece intacto.
3. La nota se inyecta dentro del `<aside>` correspondiente, justo antes
   de su etiqueta de cierre.

## 6. Contrato de Metadatos de Salida (YAML)

The dictionary returned by the `process()` method must strictly implement this schema to populate the global pipeline telemetry:

```yaml
footnote_processing:
  strategy_applied: "ParameterizedFootnoteStrategy:param_fn_a4b2c1d9"
  processing_status: PipelineStatus.SUCCESS.value                  # [success, default, unrecognized]
  anomalies_detected: []                        # Accumulated records during triage: e.g., ["inline", "ocr"]
  notes_count: 12                               # Exact integer count of notes processed in this resource
  execution_timestamp: "2026-06-29T13:30:00Z"   # Dynamic timestamp generated at runtime in ISO-8601 UTC format

````
