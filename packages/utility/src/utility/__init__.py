"""
````markdown
## 1. Purpose and Scope

The `book_loader` package is the exclusive entry point for decompressing,
parsing, and exposing source book containers (EPUB, FB2) as `BeautifulSoup`
trees to the orchestrator. It encapsulates every format-specific concern —
container structure, manifest parsing, parser selection — so that no
processing module downstream (`structural_sanitizer`, `footnote_processor`,
`table_normalizer`, etc.) ever needs to know or care which source format
produced the soup it received.

* **Orchestrator-Only Visibility:** This is the single exception to the rest
  of the library's uniform `BeautifulSoup`-in / `BeautifulSoup`-out contract.
  No processing module imports or references `BaseBookLoader` or its
  subclasses. The orchestrator resolves everything it needs from this layer
  (soups, manifest metadata, native notes location) and passes plain,
  already-resolved parameters — strings, dicts, `ISOLanguageCode` instances —
  into the processing pipeline. This preserves the library's core promise:
  it processes `Soup` objects, indifferent to their origin, whether that
  origin is an EPUB, an FB2, or in principle any other well-formed
  markup source.
* **Ingestion Only:** This package handles reading and exposing source
  content exclusively. Output serialization (Pandoc conversion, sibling
  asset directory writing, final Markdown assembly) is out of scope and
  remains the orchestrator's responsibility.
* **Thread Safety:** One loader instance is allocated per book, per
  execution thread — consistent with `BookStyleContext`'s established
  convention. A loader instance is used sequentially within a single book's
  lifecycle; this package does not implement or need internal locking.

---

## 2. Orchestrator Usage Example

```python
from dom_normalizer.core import BookStyleContext, ISOLanguageCode

with EpubBookLoader() as loader:
    loader.open(Path("mecanica_cuantica.epub"))
    manifest = loader.get_manifest_info()

    context = BookStyleContext(
        primary_language=ISOLanguageCode(manifest["primary_language"]),
    )

    native_notes_key = loader.get_native_notes_location()  # None for EPUB, likely

    for file_key, soup in loader.iterate_soups():
        # ... run the Stage 1/2/3 pipeline per chapter, using `context`
        # and passing `native_notes_key` into footnote_processor's
        # constructor as a plain string parameter ...
        pass
```

---

## 3. Explicit Non-Goals

* No output writing (Pandoc invocation, sibling directory asset writes —
  those remain `media_processor`'s and the orchestrator's responsibility).
* No web-page (arbitrary HTML) loader is specified here yet. Given the
  project's stated goal of format-agnostic Soup processing, a future
  `WebPageLoader(BaseBookLoader)` is architecturally anticipated but
  intentionally out of scope for this version.

````
"""
