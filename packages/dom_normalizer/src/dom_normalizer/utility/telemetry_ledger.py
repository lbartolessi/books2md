"""Provides a utility class for collecting telemetry across a batch run.

This module defines the `TelemetryLedger`, a simple dataclass designed to be
used by an orchestrator to aggregate metrics and errors from processing
multiple documents. It acts as a standardized container, but does not perform
any calculations or analysis itself.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TelemetryLedger:
    """An optional utility for aggregating telemetry across a batch run.

    This dataclass serves as a simple, in-memory database for an orchestrator
    to record the outcomes of processing multiple documents. It tracks summary
    statistics and collects detailed results for each document.

    No processing module requires or references this class; every module's
    `process()` method returns a self-contained metadata dictionary. This class
    is a convenience for the top-level application running the batch. It
    deliberately does not compute cross-module rollups (e.g., a single "total
    mutations" figure), as each module's schema is independent.

    Attributes:
        engine_version: The version of the processing engine.
        documents_processed: A counter for successfully processed documents.
        errors_logged: A counter for documents that failed processing.
        pipeline_runs: A list of dictionaries, where each dictionary contains
            the results or error for a single document.
    run. No processing module requires or references this class — every
    module's process() already returns a self-contained metadata dict.
    Deliberately does not compute cross-module rollups (e.g. a single
    "total mutations" figure); each module's schema is independent and this
    class has no privileged knowledge of any module's internal fields.
    Orchestrators needing a specific rollup compute it themselves by
    walking `pipeline_runs`.
    """

    engine_version: str = "unspecified"
    documents_processed: int = 0
    errors_logged: int = 0
    pipeline_runs: list[dict[str, Any]] = field(default_factory=list)

    def record_document(
        self,
        document_id: str,
        processor_telemetry: dict[str, Any],
    ) -> None:
        """Records the telemetry for a successfully processed document.

        This method increments the processed documents counter and appends the
        detailed telemetry data for a single document to the `pipeline_runs` list.

        Args:
            document_id: A unique string identifier for the document.
            processor_telemetry: A dictionary assembled by the orchestrator,
                typically mapping module names to their specific metadata output
                for this document. The shape of this dictionary is determined by
                the caller.

        Mutations:
            - Increments `self.documents_processed` by 1.
            - Appends a new dictionary to the `self.pipeline_runs` list with the
              keys "document_id" and "telemetry".
        """
        self.documents_processed += 1
        self.pipeline_runs.append(
            {"document_id": document_id, "telemetry": processor_telemetry},
        )

    def record_error(self, document_id: str, error: Exception) -> None:
        """Records a failure encountered during a document's processing.

        This method increments the error counter and appends a record of the
        failure to the `pipeline_runs` list. The exception is converted to a
        string for simple serialization.

        Args:
            document_id: A unique string identifier for the document that
                failed processing.
            error: The exception object that was caught by the orchestrator.

        Mutations:
            - Increments `self.errors_logged` by 1.
            - Appends a new dictionary to the `self.pipeline_runs` list with the
              keys "document_id" and "error".
        """
        self.errors_logged += 1
        self.pipeline_runs.append({"document_id": document_id, "error": str(error)})

    def to_dict(self) -> dict[str, Any]:
        """Exports the complete ledger as a dictionary.

        This method provides a simple way to serialize the entire state of the
        telemetry ledger, for example, to save it as a JSON file at the end of
        a batch run.

        Returns:
            A dictionary containing all collected telemetry, nested under a
            top-level `session_telemetry` key.

        Mutations:
            None.
        """
        return {
            "session_telemetry": {
                "engine_version": self.engine_version,
                "documents_processed": self.documents_processed,
                "errors_logged": self.errors_logged,
                "pipeline_runs": self.pipeline_runs,
            },
        }
