# SPECIFICATION: `accessibility_normalizer` PACKAGE (Version 1.0 - ACCESSIBILITY LANDMARK TRANSLATION)

## 1. Purpose and Scope

The `accessibility_normalizer` module is a semantic enrichment layer (Stage 2 -
Document Structure Layer) for the DPUB-ARIA landmarks and roles that fall
**outside footnote/endnote vocabulary** — that territory belongs exclusively to
`footnote_processor`'s `AriaDpubStrategy` (Stage A). This module's function is
not to keep raw ARIA markup in the Markdown (which would be ignored by the
renderer), but to intercept the remaining accessibility attributes from the
original XHTML (`epub:type` and `doc-*` roles) and translate them into native
structural blocks or fenced blocks with semantic classes.

### Why it is critical for RAG and LLMs

* **Footnote Isolation (`doc-footnote`):** It prevents an explanatory note inserted in the middle of a text flow from contaminating the main paragraph's embedding by abstracting it into its own indexable block or a real Markdown footnote.
* **Perimeter Noise Filtering (`doc-bibliography`, `doc-toc`):** It allows the data loader to immediately identify which parts of the book are indexes or lengthy lists of bibliographic references, giving you the option to exclude them from the RAG to avoid false positives in vector searches.
* **Page Citation Preservation (`doc-pagebreak`):** Digital page break milestones allow the LLM to know exactly on which physical page of the printed book a piece of data is located, facilitating exact academic citation without breaking the continuity of the sentence.

---

## 2. Semantic Translation Matrix (From XHTML to Protected Markdown)

The processor analyzes the in-memory DOM, searching for specific attributes and mutating the node according to the following conversion rules:

| Original XHTML Attribute (EPUB3 / ARIA) | Editorial Meaning | DOM Mutation (Injected Class) | Final Destination in Markdown (Stage 4) |
| --- | --- | --- | --- |
| `epub:type="pagebreak"`<br>

<br>`role="doc-pagebreak"` | Physical page limit indicator. | Wrapped in a comment or span with page ID. | `` (Invisible anchor for citation). |
| `role="doc-bibliography"` | List of references and sources. | `<div class="appendix-block bibliography">` | `::: {.bibliography}` (Isolated for chunker control). |
| `role="doc-glossary"` | Glossary of technical terms. | `<div class="appendix-block glossary">` | `::: {.glossary}` (Treated as a key-value dictionary for the RAG). |

---

## 3. Critical Processing Cases

### CASE A: Indexing of Page Milestones (Exact Academic Citation)

* **Condition:** An empty element (usually a `<span>` or `<div>`) is detected acting as a physical page marker via the `role="doc-pagebreak"` attribute.
* **Action:** The element is not removed, but mutated into a native `bs4.Comment`
  node inserted at the same DOM position, carrying the page ID as its content.
  This is a structural DOM mutation, not literal Markdown text — the invisible
  comment survives Pandoc's AST conversion as a raw inline comment, readable
  only by chunker logic inspecting the intermediate representation.
* **Conversion:**

```markdown
Light propagates in a vacuum at a constant speed. This constant is fundamental...

```

---

## 4. The Protection Shield in Stage 4

As in the previous modules, the use of `.bibliography` or `.glossary` classes generates Pandoc's structural fences (`::: {.glossary}`).

When the **Stage 4** post-processor operates on the document:

1. **It activates the protection shield** upon entering these fences.
2. It knows that the inner text of the glossary or bibliography has a very high-density list structure. The line flattener respects the line breaks between definitions, preventing the dictionary of terms from becoming an amorphous mass of text.
3. It allows applying a metadata tag to the chunker: `chunk_strategy: "no_split"` to ensure that a glossary definition is never split in the middle.
   * The `no_split` directive is carried as a native DOM attribute on the fenced
     container: `<div class="appendix-block glossary" data-chunk-strategy="no_split">`.
     Pandoc's fenced-div translation preserves custom attributes verbatim, making
     this value available to the Stage 4 chunker without any Markdown-level
     injection.

---

## 5. Object Architecture Template

```python
from bs4 import BeautifulSoup, Tag, Comment
from dom_normalizer.core import BookStyleContext, PipelineStatus
from dom_normalizer.core import get_utc_timestamp

class AccessibilityNormalizer:
    def __init__(self, context: BookStyleContext) -> None:
        self.context = context
        self.page_breaks_anchored = 0
        self.bibliography_found = False
        self.glossary_found = False

    def process(self, soup: BeautifulSoup) -> Tuple[BeautifulSoup, dict]:
        """
        Translates remaining DPUB-ARIA landmarks (pagebreak, bibliography, glossary)
        into native fenced-div/comment DOM structures. Footnote-related roles are
        explicitly out of scope — owned exclusively by footnote_processor's
        AriaDpubStrategy.
        """
        if self.context.is_inside_code_block(soup):
            return soup, {"status": PipelineStatus.IDLE.value}

        self._anchor_page_breaks(soup)
        self._wrap_bibliography(soup)
        self._wrap_glossary(soup)

        status = PipelineStatus.SUCCESS.value if (
            self.page_breaks_anchored > 0 or self.bibliography_found or self.glossary_found
        ) else PipelineStatus.IDLE.value

        metadata = {
            "accessibility_normalization": {
                "page_breaks_anchored": self.page_breaks_anchored,
                "structural_landmarks_found": {
                    "bibliography": self.bibliography_found,
                    "glossary": self.glossary_found
                },
                "status": status,
                "execution_timestamp": get_utc_timestamp()
            }
        }
        return soup, metadata

    def _anchor_page_breaks(self, soup: BeautifulSoup) -> None:
        for node in soup.find_all(attrs={"role": "doc-pagebreak"}):
            page_id = node.get("id") or node.get("title", "")
            comment = Comment(f" page-break: {page_id} ")
            node.replace_with(comment)
            self.page_breaks_anchored += 1
```

---

## 6. Output Metadata Contract (YAML)

The module generates a map of the book's hidden infrastructure so the pipeline can decide what to index and what to ignore:

```yaml
accessibility_normalization:
  page_breaks_anchored: 312
  structural_landmarks_found:
    bibliography: true
    glossary: false
  status: "success"   # Canonical PipelineStatus: [success, idle, error]
  execution_timestamp: "..."
```
