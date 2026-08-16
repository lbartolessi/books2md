# ARCHITECTURE SPECIFICATION: `media_processor` PACKAGE (Version 1.2)

## 1. Purpose and Scope

The `media_processor` module is a structural sanitization and multimedia asset extraction engine (Stage 2 - Document Structure Layer). Its main objective is to purge embedded binary noise within the EPUB XHTML, organize local resources into a strictly portable file structure, and prepare semantic multimedia pointers so that **Pandoc** and the **Stage 4** post-processor generate an optimized Markdown output for RAG and cross-compilation (LaTeX/Web) systems.

* **Pipeline Order Contract:** This component executes concurrently across separated chapters within Stage 2. It requires total isolation from inline formatting passes, operating directly on the core DOM tree prior to text flattening or paragraph joining.

### The Core Problem in RAG and Portability

* **Base64 Bloat:** Images or audio embedded as binary text strings (`data:image/...;base64`) exponentially multiply file sizes, pollute semantic chunk tokenization, and corrupt embedding vectors.
* **Path Orphans:** Absolute or chaotic paths inside the virtual EPUB container break visual references when the final Markdown file is moved.
* **Blind Interactives:** Heavy web elements (advertising `iframes`, CSS/JS animations, interactive objects) represent a semantic black hole for LLMs and break compilation to high-quality static formats like LaTeX.

### 1.1. Architectural Portability Decision (Removal of File-Size Guard Rails)

* **The Rule:** The engine extracts and copies **all** valid internal audio and video resources discovered in the container directly into the portable layout directory without size thresholds.
* **The Rationale:** Any multimedia asset explicitly packaged *inside* a standard EPUB container has already been budgeted, compressed, and optimized by the editorial publisher for digital distribution. Enforcing an arbitrary threshold (e.g., 50MB) within the parser would break legitimate, self-contained educational or language books. Pre-extraction file sizes cannot be audited safely without introducing massive disk overhead, so complete resource porting is mandated to guarantee rendering fidelity.

---

## 2. Portable Storage Structure (Sibling Directory)

To guarantee immunity against file collisions and ensure strict document portability, media processing is governed by the **Sibling Directory Rule**:

1. If the target Markdown file is written as `path/to/book/quantum_mechanics.md`, the processor creates a contiguous asset directory with the identical base name: `path/to/book/quantum_mechanics/`.
2. **Concurrency Boundary Note:** This module holds no long-lived internal
   state between calls to `process()`, and all output paths are deterministic
   given the same inputs. Because the sibling directory name is derived
   deterministically from the book's own filename, and each book is owned
   by a single worker for the duration of its processing, no cross-worker
   directory collision is possible by construction. Within a single book,
   if chapters are processed in parallel and reference a shared asset (e.g.,
   a repeated header logo), content-addressable storage (SHA-256-based
   naming, Layer A) makes the resulting concurrent writes idempotent without
   requiring synchronization. Sibling directory creation should use an
   idempotent call (e.g., `os.makedirs(..., exist_ok=True)`) to safely
   tolerate near-simultaneous creation attempts from parallel chapter
   workers within the same book. No additional synchronization primitives
   are required by or provided within this module; any concurrency model
   beyond this remains the responsibility of the orchestrating application.
3. To preserve the original EPUB hierarchy and avoid overwrites, the processor maps the internal container structure:
   * `quantum_mechanics/images/ch01/fig1.png`
   * `quantum_mechanics/audio/ch01/pronunciation.mp3`
   * `quantum_mechanics/video/ch01/exercise.mp4`
4. All resources extracted directly from text streams (Base64) are dumped into a dedicated subfolder using unique cryptographic hashes to enforce strict deduplication:

* `quantum_mechanics/extracted/asset_[sha256_hash].png`

---

## 3. DOM Processing Layers (BeautifulSoup4)

The engine operates locally and in memory over the XHTML syntactic tree, executing three sequential logical layers:

### 3.1. Layer A: Base64 Extraction and Sanitization (Token Saver)

* **Condition:** Detects any graphic tag (`<img>`, `<image>`) or multimedia object whose `src` or `href` attribute begins with the data scheme `data:image/` or `data:audio/`.
* **Action:**

1. Isolates the Base64 text payload and decodes it into an in-memory binary stream.
2. Computes the SHA-256 hash of the binary content to serve as a unique identifier.
3. Writes the physical asset to the sibling directory: `[book]/extracted/asset_[hash].[ext]`.
4. Mutates the DOM attribute, substituting the massive Base64 string with the clean relative path: `src="quantum_mechanics/extracted/asset_[hash].[ext]"`.

### 3.2. Layer B: Local Asset Extraction (Audio and Video Portfolios)

* **Condition:** Identifies local multimedia assets: elements structured as `<audio>`, native `<video>` containers, or generic `<object>` tags containing local media extensions.
* **Action:** The processor extracts the physical audio or video file and routes it strictly to its respective target subdirectory (`[book]/audio/...` or `[book]/video/...`). Telemetry tracks audio and video streams using independent granular counters to prevent analytical distortion. SHA-256 content hashes are calculated to enforce strict deduplication of identical media files. Complex or proprietary wrappers are stripped and replaced with simplified native HTML5 tags that Pandoc processes natively:

```html
<audio src="quantum_mechanics/audio/unit1/word01.mp3" controls="controls">
  Audio: Word pronunciation
</audio>

```

### 3.3. Layer C: External Video Blocks & Interactives (Semantic Pointers)

* **Condition:** Encounters an `<iframe>`, `<embed>`, or `<object>` tag pointing to external platforms, evaluated via domain verification against known video targets.

```python
VIDEO_DOMAIN_RX = re.compile(r'(youtube\.com|youtu\.be|vimeo\.com)', re.IGNORECASE)

```

* **Action:** **Semantic Isolation (Structural Symmetry).** The processor extracts the external destination URL (*pointer*) and the thumbnail image (*thumbnail*) if available. If no thumbnail is provided by the manifest, the engine automatically generates a standardized placeholder vector asset (neutral SVG with a media icon overlay) to ensure consistent visual tracking. Content deduplication via SHA-256 hashing is enforced on all collected preview assets. The element is wrapped inside a guarded layout block:

```html
<div class="protected video-block" data-video-src="https://www.youtube.com/watch?v=dQw4w9WgXcQ">
  <img src="quantum_mechanics/images/thumbnails/video_ch1.jpg" alt="Video: Uncertainty Principle Demonstration" />
</div>

```

### 3.4. Layer D: Defensive Degradation of Executable and Canvas Artifacts

* **Condition:** Executable script nodes (`<script>`) or dynamic graphic canvases (`<canvas>`) that do not supply indexable text streams and disrupt portable book mechanics.
* **Action:** Complete purging of the invasive DOM node and substitution with a clean, descriptive text placeholder readable by RAG chunkers and LLM context windows:

```html
<p class="media-placeholder"><em>[Multimedia Element Omitted: Script or interactive component unsupported by portable layouts]</em></p>

```

---

## 4. Formatting Contracts for Pandoc and Post-Processing (Phase 4)

The normalized XHTML output is passed to Pandoc, which generates the following intermediate Markdown block structures:

### 4.1. Video Block Translation (Pandoc Fenced Div)

Pandoc cleanly translates the `<div>` wrapper and its classes into a structural fenced block:

```markdown
::: {.protected .video-block data-video-src="https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
![Video: Uncertainty Principle Demonstration](quantum_mechanics/images/thumbnails/video_ch1.jpg)
:::

```

### 4.2. Protection and Immunity in Phase 4

When the text processor (`unwrap_lines` / `TextNormalizer`) executes line-by-line streaming passes over the intermediate Markdown file:

1. Upon matching the opening marker `::: {.protected .video-block`, **the system activates the structural shielding**.
2. The prose flattening and line-joining routine is completely deactivated, preventing URL corruption, metadata line merging, or thumbnail path destruction.
3. Upon matching the closing fence `:::`, the protective shield is deactivated.

### 4.3. Final Semantic Mutation (Definitive RAG / LaTeX Output)

During the final cleanup pass of Phase 4, immediately prior to consolidating the target text file, the state machine dissolves the technical fences and rewrites the block using standard hyperlinked image Markdown syntax:

```markdown
[![Video: Uncertainty Principle Demonstration](quantum_mechanics/images/thumbnails/video_ch1.jpg)](https://www.youtube.com/watch?v=dQw4w9WgXcQ)

```

**System Output Profile:**

* **For RAG / LLM Execution:** The chunker indexes a clean block containing an explicit text description of the video along with its source reference link.
* **For LaTeX Compilation:** This structure natively translates into a hyperlinked command: `\href{url}{\includegraphics{...}}`, yielding a dynamic PDF document where the preview thumbnail serves as an interactive button that opens the external resource inside the user's web browser.

---

### 4.4. Algorithmic Implementation Template

```python
import os
import re
import hashlib
from typing import Tuple
from bs4 import BeautifulSoup, Tag
from dom_normalizer.core import BookStyleContext, PipelineStatus
from dom_normalizer.core import get_utc_timestamp

class MediaProcessor:
    """
    Extracts, deduplicates, and structures multimedia components into a portable sibling repository.
    Removes embedded Base64 overhead and protects interactive blocks via structural code shields.
    """
    def __init__(self, context: BookStyleContext, book_base_name: str, output_directory: str):
        self.context = context
        self.book_base_name = book_base_name
        self.output_dir = output_directory
        self.sibling_asset_dir = os.path.join(output_directory, book_base_name)
        
        self.base64_count = 0
        self.audio_count = 0
        self.local_video_count = 0
        self.external_video_count = 0
        self.purged_count = 0
        
        self.VIDEO_DOMAIN_RX = re.compile(r'(youtube\.com|youtu\.be|vimeo\.com)', re.IGNORECASE)
        self.AUDIO_EXTENSIONS = ['.mp3', '.wav', '.ogg']
        self.VIDEO_EXTENSIONS = ['.mp4', '.mkv', '.webm']

    def _get_sha256_hash(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def process(self, soup: BeautifulSoup) -> Tuple[BeautifulSoup, dict]:
        """
        Scans the DOM tree executing multi-layer asset extraction and protection.
        """
        for media_tag in soup.find_all(['img', 'image', 'audio', 'video', 'iframe', 'embed', 'object', 'script', 'canvas']):
            
            # 1. Structural Code Shield Guard Clause
            if self.context.is_inside_code_block(media_tag):
                continue
                
            # Layer A: Base64 Handling
            if media_tag.name in ['img', 'image'] and str(media_tag.get('src', '')).startswith('data:'):
                self.base64_count += 1
                continue
                
            # Layer B: Local Asset Extraction (Audio and Objects)
            is_audio_obj = media_tag.name == 'object' and any(
                str(media_tag.get('data', '')).endswith(ext) for ext in self.AUDIO_EXTENSIONS
            )
            if media_tag.name == 'audio' or is_audio_obj:
                self.audio_count += 1
                continue

            # Layer B-bis: Local Asset Extraction (Native Video and Objects)
            is_video_obj = media_tag.name == 'object' and any(
                str(media_tag.get('data', '')).endswith(ext) for ext in self.VIDEO_EXTENSIONS
            )
            if media_tag.name == 'video' or is_video_obj:
                self.local_video_count += 1
                continue
                
            # Layer C: Interactive Video Pointers (External)
            if media_tag.name in ['iframe', 'embed', 'object']:
                resource_url = str(media_tag.get('src', '')) + str(media_tag.get('data', ''))
                if self.VIDEO_DOMAIN_RX.search(resource_url):
                    self.external_video_count += 1
                    continue
                
            # Layer D: Quantitative Defensive Degradation (Pure scripts or canvases)
            if media_tag.name in ['script', 'canvas']:
                self.purged_count += 1
                placeholder = soup.new_tag("p", attrs={"class": "media-placeholder"})
                placeholder.string = "[Multimedia Element Omitted: Script or interactive component]"
                media_tag.replace_with(placeholder)

        total_mutations = (self.base64_count + self.audio_count + 
                           self.local_video_count + self.external_video_count + 
                           self.purged_count)
        status_value = PipelineStatus.SUCCESS.value if total_mutations > 0 else PipelineStatus.IDLE.value

        metadata = {
            "media_processing": {
                "base64_images_extracted": self.base64_count,
                "local_audio_files_mapped": self.audio_count,
                "local_video_files_mapped": self.local_video_count,
                "external_videos_identified": self.external_video_count,
                "unsupported_media_purged": self.purged_count,
                "sibling_directory_path": f"{self.book_base_name}/",
                "status": status_value,
                "execution_timestamp": get_utc_timestamp()
            }
        }
        return soup, metadata

```

---

## 5. Output Metadata Contract (YAML)

```yaml
media_processing:
  base64_images_extracted: 42         # Strings de Base64 convertidas a archivos físicos
  local_audio_files_mapped: 12        # Archivos de audio locales extraídos y normalizados
  local_video_files_mapped: 2         # Archivos de vídeo locales (e.g. MP4) extraídos al directorio hermano
  external_videos_identified: 3       # Vídeos externos aislados en bloques estructurados
  unsupported_media_purged: 1         # Bloques de script o canvas eliminados del árbol
  sibling_directory_path: "quantum_mechanics/"
  status: "success"                    # Allowed values matching PipelineStatus Enum: success, idle, error
  execution_timestamp: "2026-06-30T22:28:00Z"

```
