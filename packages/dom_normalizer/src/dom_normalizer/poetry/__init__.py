"""A geometric and forensic engine for isolating and normalizing poetic verse.

This package operates as a Stage 2 processor, executing strictly after the
`blockquote_processor`. Its primary function is to identify blocks of text that
are structurally poetry, using a combination of explicit markup, layout
heuristics, and statistical text analysis. Once identified, it mutates these
blocks into a standardized, Pandoc-compatible HTML structure.

The engine uses a tiered entry system: it always inspects `<blockquote>`
elements, and if the book is flagged as "High Poetry Priority" in its
metadata, it performs a global scan for other potential verse structures.

Analytical Blueprint:
---------------------

Based on the specification, the following logic will be mapped to the class
methods:

Global Free Functions (Module Level):
    - None present in the skeleton.

Class Methods (StructuralMatcher):
    - __init__: Initializes the matcher with configuration from the shared
      `BookStyleContext`. It loads the `structural_registry_path` and the
      provisional thresholds: `br_density_threshold`,
      `dialogue_exclusion_threshold` (0.40), and `enjambment_ratio_threshold` (0.60).
    - match: A read-only observer that analyzes a target `Tag`. It checks for
      matches in three modes: `container` (explicit registry match), `table`
      (valid `<table>` with `<tr>` and `<td>`), and `separator` (sequence of
      `<p>` tags). The `separator` mode is pre-filtered by a "Dialogue Exclusion
      Guard" which rejects sequences where >40% of lines match dialogue
      signatures (`DIALOGUE_DASH_RX` or `SPEAKER_LABEL_RX`). If not rejected, it
      applies the "Compound Classification Rule": a match occurs if Line Density
      is below `br_density_threshold` OR Enjambment Ratio is above
      `enjambment_ratio_threshold`. It returns a dictionary detailing the match
      type or the specific reason for rejection.

Class Methods (PoetryNormalizer):
    - __init__: Initializes the normalizer, creating an instance of
      `StructuralMatcher` and resetting telemetry counters: `detected_poems_count`,
      `dialogue_blocks_excluded`, and `geometric_rejections`.
    - process: The main orchestration method. It identifies candidate blocks
      (all `<blockquote>` elements, and other blocks if the book has "High
      Poetry Priority"). For each candidate, it calls `self.matcher.match()`.
      - If a match is found, it triggers a DOM mutation, transforming the block
        into a `<div class="poetry-block">` containing
        `<div class="verse-line"><p>...</p></div>` structures. It preserves
        the parent `<blockquote>` if present. It calculates and adds
        `data-verse-indent` attributes and converts stanza breaks to
        `<hr class="stanza-break"/>`. It increments `detected_poems_count`.
      - If the match is rejected, it increments `dialogue_blocks_excluded` or
        `geometric_rejections` based on the `rejection_reason`.
      - Finally, it returns the mutated soup and a metadata dictionary
        conforming to the YAML contract.
"""

# This is a valid relative import, but Pylint sometimes struggles with resolving
# it during static analysis. Disabling the error is the standard workaround.
from .normalizer import PoetryNormalizer  # pylint: disable=import-error

__all__ = ["PoetryNormalizer"]
