# Role and Audit Guidelines

Act as a Python architecture and code review expert. You are going to audit the project files for `dom_normalizer` located in the `src/dom_normalizer` directory, formally evaluating compliance with the `dom_normalizer` Architectural Principles:

- Inversion of Control (IoC) and explicit Dependency Injection: Verify that there are no internal model instances, hidden global states, or tightly coupled singletons. Each component must receive its dependencies explicitly.
- Mutable Context (`BookStyleContext`) and Fault Isolation: Check that error handling follows localized degradation guidelines (Pass-Through Guard Clause / node-level rescues without collapsing the main pipeline).

Generate a concise report structured exactly as follows:

- **Architectural Principles Assessment:** (Compliance with IoC, explicit injection, fault isolation, and separation of concerns).
- **Real architectural issues (if any).** - **Repair Prompt:** (A technical prompt ready to use in an LLM that precisely and automatically orders the refactoring of the failures found in this group).