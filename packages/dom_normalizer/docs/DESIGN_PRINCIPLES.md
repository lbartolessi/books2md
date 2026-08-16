# SPECIFICATION: ARCHITECTURE CORE, DEPENDENCY INJECTION, AND BOOTSTRAP LIFECYCLE (v1.4 - MUTABLE CONVERSIONS)

## 1. Architectural Principles & Design Philosophy

The `dom_normalizer` engine adheres to a strict, local-first architectural paradigm designed for air-gapped, resource-constrained environment deployments.

* **Inversion of Control (IoC) for Injected Services:** The library strictly forbids internal instantiation or automated downloading of machine-learning models from remote hubs. Top-level orchestrators are the exclusive owners of model lifecycles and configuration provisions.
* **Air-Gapped Local-First Autonomy:** No remote network handshake or repository registry call (e.g., Hugging Face Hub downloads) is allowed. All weights must live locally on disk within the path boundaries designated at boot time.
* **Unified Mutable Context Architecture (The Service Bridge):** Pipeline tasks share a mutable `EpubContext`. This context hosts a reference to the global `ApplicationContainer` and state registries (such as multi-chapter DOM trees and cross-reference indices), allowing seamless state modification without global side effects.
* **Explicit Dependency Injection (DI):** Every structural parser or normalizer component must receive its state and external boundaries explicitly. Module-level states or hardcoded system singletons are strictly prohibited.
* **Sovereign Local Execution & Fault Isolation:** No untamed exception is allowed to crash the master batch processing orchestrator. Failures at the node, chapter, or model level must cause deterministic, localized degradation.

---

## 2. Error Insulation and Fault Tolerance Matrix

To safeguard automated mass batched conversions, execution exceptions are strictly isolated at distinct architectural boundaries.

| Exception Scope | Caught Boundary | Core System Rescue Pattern |
| --- | --- | --- |
| **Registry Corruption / I/O Loss** | Stage 2 (Wiring) | Catches `FileNotFoundError` or `JSONDecodeError` during pattern registry loading. Logs a system warning to stderr, fallbacks immediately to an empty python dictionary configuration (`{}`), sets structural matching behavior to automatic fallback, and continues boot execution safely. |
| **Dynamic Agent Plugin Load Failure** | Runtime Discovery | Catches `ImportError`, `AttributeError`, or `SyntaxError` while parsing the `dynamic_plugins_path` directory. Increments `errors_logged`, ignores the specific corrupted plugin file, logs a diagnostic traceback, and falls back cleanly to standard packaged immutable strategies. |
| **Model Swapping / VRAM Allocation Crash** | Orchestrator / Component Entry | If the top-level orchestrator purges the VRAM and fails to reload the model (or passes a `None` / unallocated object reference), the `LinguisticPeritator` catches the null state or any underlying PyTorch `RuntimeError`. It drops its internal status to `is_ia_capable = False`, fallbacks natively to *Strategy C (Sovereign CPU Degradation)*, and returns `False` for semantic checks without crashing the pipeline loop. |
| **DOM Mutation Element Malformation** | Sub-Processor / Chapter Loop | Catches any unhandled element mutation exception (e.g., IndexError, AttributeError during soup manipulation) inside individual processor layers (`PoetryNormalizer`, `FootnoteProcessor`, etc.). The routine instantly aborts mutations on that single specific node string, executes the **Pass-Through Guard Clause** to restore the node context to its original raw layout block, appends the error details to the telemetry ledger, and continues processing subsequent sibling elements. |

---

## 3. Telemetry Ledger and Production Audit Contracts

Every operational stage must append state updates cleanly back to the shared `telemetry_ledger` inside the application container using structured dictionary arrays. String interpolations or arbitrary decoupled outputs are forbidden.

```json
{
  "session_telemetry": {
    "engine_version": "2.3.0",
    "hardware_device_assigned": "cuda:0",
    "total_execution_duration_seconds": 124.52,
    "document_metrics": {
      "document_id": "urn:uuid:978-84-123456-7-8",
      "high_poetry_priority_triggered": true,
      "chapters_mutated": 12,
      "total_poetry_blocks_transformed": 4
    }
  }
}

```
