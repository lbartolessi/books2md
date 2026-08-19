"""A pure, non-mutating observer engine for footnote structural analysis.

This module provides the `ForensicPatternAnalyzer`, a pure observer that runs
as part of the Stage D (Forensic Triage) step in the `footnote_processor`. Its
sole responsibility is to apply graph-topology and statistical heuristics to
the DOM to isolate, extract, and quantify structural invariants related to
footnote systems. It feeds this clean, structured data to the
`StructuralStrategyCompiler`.

Analytical Blueprint:
---------------------

Based on the specification, the following logic will be mapped to the class
methods:

Global Free Functions (Module Level):
    - None present in the skeleton.

Class Methods (ForensicPatternAnalyzer):
    - __init__: Initializes the analyzer with the shared `BookStyleContext`.
    - analyze_footnote_anomaly: Orchestrates the 5-step forensic pipeline. It
      calls the helper methods in sequence to filter anchors, extract a common
      `href` pattern, locate the note body cluster, and verify bidirectional
      linking. It raises a `ForensicAnalysisError` if the symmetry check fails.
    - _filter_and_collect_candidate_anchors: Implements Stage 1 (Sieve). It
      scans all `<a>` tags and discards any that are external links, point to
      heading tags (TOC entries), or lack a local or nearby parent `id` attribute.
    - _extract_isomorphic_href_pattern: Implements Stage 2 (Isomorphic Extraction).
      It computes the common prefix of `href` fragments and generates a regex
      (e.g., `f"^{common_prefix}\\d+"`) if the prefix is long enough, otherwise
      a wildcard. It returns the regex and the filtered group of anchors.
    - _locate_topological_cluster: Implements Stage 3 (Topological Check). It
      determines if note bodies are clustered in a single "donor_file" (>=80%
      density) or at the "end_of_section" as adjacent siblings.
    - _verify_bidirectional_symmetry: Implements Stage 4 (Symmetry Verification).
      For each callout/body pair, it verifies that the body contains a back-link
      pointing to the callout's `id`. It returns only the pairs that satisfy
      this bipartite graph invariant.
"""

from __future__ import annotations

import logging
import os
from enum import StrEnum

from bs4 import BeautifulSoup, Tag

from dom_normalizer.core import BookStyleContext

log = logging.getLogger(__name__)


class ForensicFailure(StrEnum):
    """Enumerates the specific failure points in the forensic analysis pipeline."""

    NO_CANDIDATES = (
        "Forensic analysis failed at Stage 1: No candidate anchors for footnote "
        "callouts could be identified."
    )
    NO_STRUCTURAL_GROUP = (
        "Forensic analysis failed at Stage 2: No structural group of footnote "
        "callouts could be isolated from candidate anchors."
    )
    NO_TARGET_BODIES = (
        "Forensic analysis failed at Stage 3: Could not locate any target note bodies."
    )
    NO_CLEAR_TOPOLOGY = (
        "Forensic analysis failed at Stage 3: Could not determine a clear footnote "
        "body topology (neither 'donor_file' density met nor explicit "
        "'end_of_section' pattern detected)."
    )
    SYMMETRY_CHECK_FAILED = (
        "Forensic analysis failed at Stage 4: Bidirectional symmetry check failed. "
        "Validated pairs: {validated_count}, Structural group size: {group_size}."
    )


class ForensicAnalysisError(Exception):
    """Raised when the forensic analyzer encounters an irreconcilable mathematical violation in the DOM."""


class ForensicPatternAnalyzer:
    """A pure observer engine for discovering unknown footnote patterns.

    This class implements the Stage D (Forensic Triage) of the footnote
    processing pipeline. It acts as a pure, non-mutating observer that applies
    a series of graph-topology and statistical heuristics to the entire DOM
    to isolate, extract, and quantify the structural invariants of a previously
    unseen footnote system.

    The analysis is a 5-step pipeline that verifies the mathematical properties
    of a potential footnote system, most importantly the bidirectional symmetry
    between callouts and bodies. If a robust pattern is confirmed, it returns
    the isolated invariants to the `StructuralStrategyCompiler` to be persisted
    as a new, declarative strategy.

    Attributes:
        context (BookStyleContext): The shared context for the book, providing
            access to global configuration.
    """

    def __init__(self, context: BookStyleContext) -> None:
        """Initializes the forensic engine with the book's context.

        Args:
            context (BookStyleContext): The shared context for the book, providing
                access to configuration like `min_pattern_length`.

        Returns:
            None

        Raises:
            None

        Mutations:
            - Sets `self.context` to the provided context object.

        Rules & Limits:
            - Instance Lifecycle: Assumes this instance is scoped to a single book.
        """
        self.context = context

    def analyze_footnote_anomaly(
        self,
        soups: dict[str, BeautifulSoup],
    ) -> tuple[Tag, Tag, str, str]:
        """Executes the 5-step invariant bipartite graph algorithm for footnotes.

        This is the main entry point for the analyzer. It orchestrates the
        forensic pipeline to identify the structural pattern of a footnote
        system when all static and parameterized strategies have failed.

        The pipeline consists of 5 stages:
            1.  **Sieve Anchors:** All `<a>` tags are filtered to find potential
                footnote callouts, discarding external links and TOC entries.
            2.  **Extract Pattern:** A common `href` prefix is extracted from the
                candidates to isolate a structurally related group.
            3.  **Locate Cluster:** The physical location (topology) of the note
                bodies is determined by analyzing the `href` targets.
            4.  **Verify Symmetry:** The bidirectional links between callouts and
                bodies are verified to confirm a valid bipartite graph.
            5.  **Final Validation:** The overall symmetry of the system is checked
                against a threshold to ensure a robust pattern was found.

        Args:
            soups (dict[str, BeautifulSoup]): A dictionary mapping file keys to
                their corresponding BeautifulSoup objects for the entire book.

        Returns:
            tuple[Tag, Tag, str, str]: A tuple containing a sample callout tag,
                a sample body tag, the detected CSS selector for callouts, and
                the topology location string ('donor_file' or 'end_of_section').

        Raises:
            ForensicAnalysisError: If any stage of the analysis fails to find a
                valid, symmetrical footnote system.
            Exception: Per Global Directive #1, any unexpected native exceptions
                will be caught, logged as CRITICAL, and re-raised.

        Mutations:
            None. This is a pure observer engine.
        """
        try:
            return self._run_analysis_pipeline(soups)
        except ForensicAnalysisError:
            # Re-raise controlled analysis failures without critical logging.
            raise
        except Exception:
            log.critical(
                "Unexpected error during forensic footnote analysis.",
                exc_info=True,
            )
            raise

    def _run_analysis_pipeline(
        self,
        soups: dict[str, BeautifulSoup],
    ) -> tuple[Tag, Tag, str, str]:
        """Orchestrates the 5-stage forensic analysis pipeline.

        This method centralizes the execution flow, including pre-computing
        data to avoid redundant DOM traversals in later stages.
        """
        # Pre-computation to avoid repeated traversals
        toc_target_ids, all_targets_by_id = self._precompute_book_data(soups)

        candidate_anchors = self._run_stage1_sieve_anchors(soups, toc_target_ids)
        detected_selector, structural_group = self._run_stage2_extract_pattern(
            candidate_anchors,
        )
        topology_location, target_bodies = self._run_stage3_locate_cluster(
            structural_group,
            all_targets_by_id,
        )
        validated_pairs = self._run_stage4_verify_symmetry(
            structural_group,
            target_bodies,
        )
        self._run_stage5_final_validation(validated_pairs, structural_group)

        # On success, return a sample pair and the detected invariants
        sample_callout, sample_body = validated_pairs[0]
        return sample_callout, sample_body, detected_selector, topology_location

    def _run_stage1_sieve_anchors(
        self,
        soups: dict[str, BeautifulSoup],
        toc_target_ids: set[str],
    ) -> list[Tag]:
        """Stage 1: Sieves anchors to find potential callouts."""
        if candidate_anchors := self._filter_and_collect_candidate_anchors(
            soups,
            toc_target_ids,
        ):
            return candidate_anchors
        raise ForensicAnalysisError(ForensicFailure.NO_CANDIDATES)

    def _run_stage2_extract_pattern(
        self,
        candidate_anchors: list[Tag],
    ) -> tuple[str, list[Tag]]:
        """Stage 2: Extracts a common href pattern to isolate a structural group."""
        detected_selector, structural_group = self._extract_isomorphic_href_pattern(
            candidate_anchors,
        )
        if not structural_group:
            raise ForensicAnalysisError(ForensicFailure.NO_STRUCTURAL_GROUP)
        return detected_selector, structural_group

    def _run_stage5_final_validation(
        self,
        validated_pairs: list[tuple[Tag, Tag]],
        structural_group: list[Tag],
    ) -> None:
        """Stage 5: Final validation of the entire system's symmetry."""
        if not validated_pairs or (
            len(validated_pairs) < len(structural_group) * self.context.config.footnote_symmetry_threshold
        ):
            raise ForensicAnalysisError(
                ForensicFailure.SYMMETRY_CHECK_FAILED.value.format(
                    validated_count=len(validated_pairs),
                    group_size=len(structural_group),
                ),
            )

    def _precompute_book_data(
        self,
        soups: dict[str, BeautifulSoup],
    ) -> tuple[set[str], dict[str, list[tuple[Tag, str]]]]:
        """Pre-computes TOC targets and a map of all element IDs across the book.

        This optimization avoids repeated full-document traversals during the
        anchor filtering and body resolution stages.

        Args:
            soups: All BeautifulSoup objects for the book.

        Returns:
            A tuple containing a set of all TOC target IDs and a dictionary
            mapping all element IDs to the tags that have them.
        """
        toc_target_ids: set[str] = set()
        all_targets_by_id: dict[str, list[tuple[Tag, str]]] = {}
        warned_duplicate_ids: set[str] = set()

        for file_key, soup in soups.items():
            for tag in soup.find_all(id=True):
                if isinstance(tag, Tag):
                    tag_id = str(tag["id"]) # pyright: ignore[reportUnknownArgumentType]
                    if tag.name in self.context.config.footnote_toc_heading_tags:
                        toc_target_ids.add(tag_id)

                    if (
                        tag_id in all_targets_by_id
                        and tag_id not in warned_duplicate_ids
                    ):
                        log.warning(
                            "Duplicate ID '#%s' found in file '%s'. This may indicate malformed HTML.",
                            tag_id,
                            file_key,
                        )
                        warned_duplicate_ids.add(tag_id)
                    all_targets_by_id.setdefault(tag_id, []).append((tag, file_key))
        return toc_target_ids, all_targets_by_id

    def _get_callout_id(self, callout: Tag) -> str | None:
        """Finds the ID of the callout or its immediate parent.

        This helper is crucial for the symmetry check, as backlinks often point
        to a container (`<p>` or `<sup>`) around the callout anchor, not the
        anchor itself.

        Args:
            callout (Tag): The callout `<a>` tag.

        Returns:
            str | None: The ID string if found, otherwise None.
        """
        if callout.get("id"):
            return str(callout["id"])
        if callout.parent and callout.parent.get("id"):
            return str(callout.parent["id"])
        return None

    def _get_href_from_anchor(self, anchor: Tag) -> str:
        """Safely extracts a single string href from an anchor tag.

        BeautifulSoup's `get` can return a string or a list of strings. This
        helper normalizes the output to a single string.

        Args:
            anchor (Tag): The anchor tag to process.

        Returns:
            str: The href value as a string, or an empty string if not found.
        """
        href_val = anchor.get("href")
        if isinstance(href_val, list):
            return href_val[0] if href_val else ""
        return href_val or ""

    def _is_toc_entry(self, href: str, toc_target_ids: set[str]) -> bool:
        """Checks if a local href points to a heading, likely a TOC entry.

        Args:
            href (str): The href attribute value of the anchor tag.
            toc_target_ids (set[str]): A pre-computed set of all heading IDs.

        Returns:
            bool: True if the href points to an h1, h2, or h3 tag anywhere in the book.
        """
        return href[1:] in toc_target_ids if href.startswith("#") else False

    def _is_valid_candidate(
        self,
        anchor: Tag,
        toc_target_ids: set[str],
    ) -> bool:
        """
        Applies a series of filters to determine if an anchor is a potential footnote callout.

        Args:
            anchor (Tag): The anchor tag to validate.
            toc_target_ids (set[str]): A pre-computed set of all heading IDs
                for efficient TOC entry checking.

        Returns:
            bool: True if the anchor is a valid candidate, False otherwise.
        """
        href = self._get_href_from_anchor(anchor)

        if not href:
            return False

        # Rule 1: Discard external links
        # Treat absolute and protocol-relative URLs as external.
        # Note: protocol-relative URLs start with `//` and should be considered external.
        if href.startswith(("http://", "https://", "//")):  # NOSONAR
            return False

        # Rule 2: Discard TOC entries
        if self._is_toc_entry(href, toc_target_ids):
            return False

        # Rule 3: Ensure a stable ID exists for back-linking.
        return bool(self._get_callout_id(anchor))

    def _filter_and_collect_candidate_anchors(
        self,
        soups: dict[str, BeautifulSoup],
        toc_target_ids: set[str],
    ) -> list[Tag]:
        """Stage 1: Scans all documents and sieves `<a>` tags for footnote candidates.

        This method filters out anchors that are clearly not part of a footnote
        system, such as external links or Table of Contents entries.

        Args:
            soups (dict[str, BeautifulSoup]): All BeautifulSoup objects for the book.
            toc_target_ids (set[str]): A pre-computed set of all heading IDs
                for efficient TOC entry checking.

        Returns:
            list[Tag]: A list of `<a>` tags that are potential footnote callouts.

        Raises:
            None

        Mutations:
            None.

        Rules & Limits:
            - An `<a>` tag is discarded if any of the following are true:
              1. Its `href` attribute starts with `http://` or `https://`. (External link)
              2. Its `href` fragment points to a target element that is an `<h1>`, `<h2>`,
                 or `<h3>`. (Table of Contents link)
              3. It lacks an `id` attribute, and its immediate parent also lacks an `id`.
                 (No stable target for a backlink)
            - Full depth traversal: Yes.
        """
        candidates = []
        for soup in soups.values():
            candidates.extend(
                anchor
                for anchor in tuple(soup.select("a[href]"))
                if self._is_valid_candidate(anchor, toc_target_ids)
            )
        return candidates

    def _extract_isomorphic_href_pattern(
        self,
        anchors: list[Tag],
    ) -> tuple[str, list[Tag]]:
        """Stage 2: Extracts a common lexical pattern from `href` attributes.

        This method analyzes the `href` fragments of candidate anchors to find a
        common prefix, which is then used to generate a CSS attribute selector
        for identifying the structural group of footnote callouts.

        Args:
            anchors (list[Tag]): The list of candidate anchors from Stage 1.

        Returns:
            tuple[str, list[Tag]]: A tuple containing the generated CSS selector string
                and the filtered list of anchors that match this pattern (the
                structural group).

        Raises:
            None

        Mutations:
            None.

        Rules & Limits:
            - All internal `href` attributes (both `#id` and `file.html#id`) are
              normalized to their fragment part (e.g., `id`) for common prefix
              computation. This ensures consistency with `_is_valid_candidate`.
            - Computes the `os.path.commonprefix` of all selected fragments.
            - If `len(common_prefix) >= self.context.config.min_pattern_length`,
              the selector is `a[href^="#{common_prefix}"]`.
            - Otherwise, the selector is a fallback `a[href^="#"]`.
            - The input `anchors` are then filtered to form the final `structural_group`.
        """
        fragments: list[str] = []
        for anchor in anchors:
            href = self._get_href_from_anchor(anchor)
            if "#" in href and (fragment := href.split("#", 1)[1]):
                fragments.append(fragment)

        if not fragments:
            return 'a[href^="#"]', []

        lexical_common_prefix = os.path.commonprefix(fragments)
        if common_prefix := self._refine_id_prefix(
            lexical_common_prefix,
            fragments,
        ):
            selector = f'a[href^="#{common_prefix}"]'
            structural_group = [
                anchor
                for anchor in anchors
                if (href := self._get_href_from_anchor(anchor))
                and href.startswith(f"#{common_prefix}")
            ]
            return selector, structural_group

        selector = 'a[href^="#"]'
        log.debug(
            "No common prefix found or prefix too short. "
            "Falling back to wildcard anchor selector '%s'.",
            selector,
        )
        structural_group = [
            anchor
            for anchor in anchors
            if (href := self._get_href_from_anchor(anchor)) and href.startswith("#")
        ]
        return selector, structural_group

    def _get_char_kind(self, ch: str) -> str:
        """Categorizes a character as 'digit', 'alpha', or 'other'."""
        if ch.isdigit():
            return "digit"
        return "alpha" if ch.isalpha() else "other"

    def _get_following_char_kinds(self, prefix: str, ids: list[str]) -> set[str]:
        """Finds the character kinds immediately following a prefix in a list of IDs."""
        following_kinds = set()
        for fid in ids:
            if not fid.startswith(prefix):
                continue
            if len(fid) == len(prefix):
                continue
            next_ch = fid[len(prefix)]
            following_kinds.add(self._get_char_kind(next_ch))
        return following_kinds

    def _refine_id_prefix(self, prefix: str, ids: list[str]) -> str | None:
        """
        Refines a lexical prefix to be ID-aware, avoiding partial token matches.

        Given a lexical prefix (e.g., "fn1" from "fn1" and "fn10"), this method
        walks backwards to find a "safe" boundary that doesn't cut through an
        alphanumeric token. The goal is to produce a prefix like "fn" instead of "fn1".

        Args:
            prefix (str): The initial lexical common prefix.
            ids (list[str]): The full list of ID fragments.

        Returns:
            str | None: A refined, token-aware prefix, or None if no suitable
                prefix can be found.
        """
        try:
            min_len = int(self.context.config.min_pattern_length)
            if min_len <= 0:
                raise ValueError
        except (ValueError, TypeError, AttributeError):
            log.warning(
                "Invalid 'min_pattern_length' in config. Cannot refine ID prefix. Value: %s",
                getattr(self.context.config, "min_pattern_length", "Not set"),
            )
            return None

        if not prefix or len(prefix) < min_len:
            return None

        refined = prefix
        while len(refined) >= min_len:
            last_kind = self._get_char_kind(refined[-1])
            following_kinds = self._get_following_char_kinds(refined, ids)

            # If no following characters, the boundary is safe.
            if not following_kinds:
                break

            # If all following characters are of the same kind as the last
            # character of the prefix, we are likely in the middle of a token.
            if len(following_kinds) == 1 and last_kind in following_kinds:
                refined = refined[:-1]  # Move boundary back.
                continue

            # Otherwise, we have found a safe boundary.
            break

        if len(refined) < min_len:
            return None

        # Final check: ensure the refined prefix still matches all original candidates.
        # This guards against edge cases where backtracking goes too far.
        for fid in ids:
            if fid.startswith(prefix) and not fid.startswith(refined):
                log.warning(
                    "ID prefix refinement failed consistency check. "
                    "Original: '%s', Refined: '%s', Failing ID: '%s'",
                    prefix,
                    refined,
                    fid,
                )
                return None

        return refined

    def _resolve_bodies_and_distribution(
        self,
        structural_group: list[Tag],
        all_targets_by_id: dict[str, list[tuple[Tag, str]]],
    ) -> tuple[list[Tag], dict[str, int]]:
        """Resolves note bodies from callouts and calculates their file distribution."""
        resolved_bodies: set[Tag] = set()
        file_distribution: dict[str, int] = {}

        for callout in structural_group:
            href = self._get_href_from_anchor(callout)
            if not href.startswith("#"):
                continue

            target_id = href[1:]
            if target_body_candidates := all_targets_by_id.get(target_id):
                for target_body, source_file in target_body_candidates:
                    resolved_bodies.add(target_body)
                    file_distribution[source_file] = (
                        file_distribution.get(source_file, 0) + 1
                    )
        return list(resolved_bodies), file_distribution

    def _run_stage3_locate_cluster(
        self,
        structural_group: list[Tag],
        all_targets_by_id: dict[str, list[tuple[Tag, str]]],
    ) -> tuple[str, list[Tag]]:
        """Stage 3: Determines the physical location of the note bodies in the DOM.

        This method resolves the `href` targets of the structural group and
        analyzes their distribution to classify the note topology.

        Args:
            structural_group (list[Tag]): The filtered group of callout anchors.
            all_targets_by_id (dict): A pre-computed map of all element IDs to
                their corresponding tags across the book.

        Returns:
            tuple[str, list[Tag]]: A tuple containing the topology location string
                ('donor_file' or 'end_of_section') and a list of the resolved
                note body `Tag` objects.

        Raises:
            None

        Mutations:
            None.

        Rules & Limits:
            - If >= 80% of the note bodies reside in the same separate file, the
              `topology_location` is marked as `"donor_file"`.
            - If the note bodies are appended at the bottom of individual chapters
              as adjacent siblings under a common parent, the `topology_location`
              is marked as `"end_of_section"`.
        """
        resolved_bodies, file_distribution = self._resolve_bodies_and_distribution(
            structural_group,
            all_targets_by_id,
        )

        if not resolved_bodies:
            raise ForensicAnalysisError(ForensicFailure.NO_TARGET_BODIES)

        total_bodies = len(resolved_bodies)
        for count in file_distribution.values():
            if (
                count / total_bodies >= self.context.config.footnote_donor_file_density_threshold
            ):
                return "donor_file", resolved_bodies

        raise ForensicAnalysisError(ForensicFailure.NO_CLEAR_TOPOLOGY)

    def _build_body_id_map(self, target_bodies: list[Tag]) -> dict[str, list[Tag]]:
        """Builds a multi-map from ID to a list of body tags that share it.

        This handles the edge case of invalid HTML where multiple elements might
        have the same ID.

        Args:
            target_bodies (list[Tag]): A list of potential note body tags.

        Returns:
            dict[str, list[Tag]]: A dictionary mapping an ID to a list of tags.
        """
        bodies_by_id: dict[str, list[Tag]] = {}
        for body in target_bodies:
            if body_id := body.get("id"):
                bodies_by_id.setdefault(str(body_id), []).append(body)
        return bodies_by_id

    def _find_symmetrical_body(
        self,
        callout: Tag,
        bodies_by_id: dict[str, list[Tag]],
    ) -> Tag | None:
        """For a given callout, finds the first body that has a valid backlink.

        Args:
            callout (Tag): The callout anchor tag.
            bodies_by_id (dict[str, list[Tag]]): The multi-map of potential note bodies.

        Returns:
            Tag | None: The matching body tag if found, otherwise None.
        """
        href = self._get_href_from_anchor(callout)
        if not href.startswith("#"):
            return None

        target_id = href[1:]
        callout_id = self._get_callout_id(callout)

        if not callout_id:
            return None

        if target_body_candidates := bodies_by_id.get(target_id):
            for target_body in target_body_candidates:
                if target_body.select_one(f'a[href="#{callout_id}"]'):
                    return target_body  # Found a valid pair
        return None

    def _run_stage4_verify_symmetry(
        self,
        structural_group: list[Tag],
        target_bodies: list[Tag],
    ) -> list[tuple[Tag, Tag]]:
        """Stage 4: Verifies the back-link invariant for each callout/body pair.

        This is the mathematical core of the analysis. For every potential
        callout-to-body link, it inspects the body to ensure a corresponding
        back-link exists, confirming a true bipartite graph structure.

        Args:
            structural_group (list[Tag]): The list of callout anchors.
            target_bodies (list[Tag]): The list of resolved note body tags.

        Returns:
            list[tuple[Tag, Tag]]: A list of `(callout, body)` tuples that have
                been successfully validated as symmetrical pairs.

        Raises:
            None

        Mutations:
            None.

        Rules & Limits:
            - For each `callout` in `structural_group`, its `href` fragment is
              matched against the `id` of each `body` in `target_bodies`.
            - Invariant 5: Upon finding a matching body, the method searches
              within that body for an `<a>` tag whose `href` fragment exactly
              matches the `id` of the original `callout`.
            - A pair is only added to the returned list if this back-link is
              found. The orchestrator is responsible for checking the final
              validation threshold.
        """
        validated_pairs: list[tuple[Tag, Tag]] = []
        bodies_by_id = self._build_body_id_map(target_bodies)

        for callout in structural_group:
            if symmetrical_body := self._find_symmetrical_body(callout, bodies_by_id):
                validated_pairs.append((callout, symmetrical_body))

        return validated_pairs
