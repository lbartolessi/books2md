"""Defines the canonical status values for pipeline metadata tracking."""

from enum import StrEnum


class PipelineStatus(StrEnum):
    """Defines the canonical status values for pipeline metadata tracking.

    This enumeration provides a controlled vocabulary for reporting the outcome of
    a processing stage, ensuring consistency across all normalizer modules.

    Attributes:
        SUCCESS: Indicates that the module executed and made changes to the DOM.
        SUCCESS_NOOP: Indicates that the module executed but made no changes, as
            the content was already compliant.
        SKIPPED: Indicates that the module was skipped and did not run (e.g., due
            to a guard clause).
        PARTIAL_SUCCESS: Indicates the module made changes but also encountered
            non-blocking anomalies (e.g., dangling references).
        ERROR: Indicates that an unrecoverable error occurred during processing.
    """

    SUCCESS = "success"
    SUCCESS_NOOP = "success_noop"
    SKIPPED = "skipped"
    PARTIAL_SUCCESS = "partial_success"
    ERROR = "error"
