# SPECIFICATION: STRUCTURAL STRATEGY COMPILER AND DECLARATIVE FACTORY (v2.1)

## 1. Scope and Design Philosophy

The `StructuralStrategyCompiler` is the authorized component responsible for the lifecycle of declarative normalization parameters at runtime. It abstracts the construction, validation, and injection of configuration signatures into the engine's JSON registries.

Under this data-driven paradigm, **inference by language models (LLMs), code agents, and injection with `importlib` are completely eliminated**. The compiler acts as a pure mathematical factory: it takes the structural invariants isolated by the `ForensicPatternAnalyzer` and packages them into clean JSON data schemas compatible with the native parameterized strategies.

---

## 2. Shared Operational Exceptions

These controlled exceptions govern critical failures of the dynamic pipeline and must be imported by the global orchestrator:

```python
class ForensicAnalysisError(Exception):
    """Raised when the forensic analyzer encounters an irreconcilable mathematical violation in the DOM."""
    pass

class RegistryWriteError(Exception):
    """Raised when the atomic persistence to the JSON registry file fails or suffers a collision."""
    pass

```

---

## 3. Manager Class Contract (`StructuralStrategyCompiler`)

```python
import json
import os
import hashlib
import tempfile
from pathlib import Path
from bs4 import Tag
from typing import Dict, Any


class StructuralStrategyCompiler:
    """
    Centralized automation factory for footnote forensic signatures exclusively.
    """
    def __init__(self, context: BookStyleContext):
        self.context = context
        self.footnote_registry_path = Path(self.context.config.footnote_registry_path)

    def compile_footnote_strategy(
        self, 
        sample_callout: Tag, 
        sample_body: Tag, 
        detected_regex: str, 
        topology_location: str
    ) -> Dict[str, Any]:
        """
        Takes the pure invariants from the forensic analyzer, generates a declarative
        configuration dictionary for Notes, persists it to the JSON registry, and returns it.
        """
        # PROBLEM 2 RESOLUTION: Pure mathematical identity independent of the document
        pattern_hash = hashlib.md5(f"{detected_regex}_{topology_location}".encode("utf-8")).hexdigest()[:8]
        pattern_id = f"param_fn_{pattern_hash}"
        
        # HIGH-LEVEL PROBLEM RESOLUTION: Robust selector to avoid massive collisions with 'div'
        if sample_body.get('class'):
            body_selector = f"{sample_body.name}.{'.'.join(sample_body['class'])}"
        elif sample_body.get('id'):
            body_selector = f"{sample_body.name}#{sample_body['id']}"
        elif sample_body.parent and sample_body.parent.name != '[document]':
            parent_cls = f".{'.'.join(sample_body.parent['class'])}" if sample_body.parent.get('class') else ""
            body_selector = f"{sample_body.parent.name}{parent_cls} > {sample_body.name}"
        else:
            # If it's a completely bare div with no classes/IDs, the pattern is not structurally
            # safe for a global parameterized strategy. Force its delegation to AnomalyStrategy.
            raise ForensicAnalysisError(
                f"Body block target '{sample_body.name}' lacks classes, IDs or structural parent specificity."
            )
        
        strategy_config = {
            "pattern_id": pattern_id,
            "forensic_signature": {
                "callout_regex": detected_regex,
                "body_topology_location": topology_location,
                "body_selector": body_selector,
                "backlink_selector": "a",
                "requires_context_extraction": topology_location == "end_of_section"
            }
        }
        
        self._write_to_registry(self.footnote_registry_path, strategy_config)
        return strategy_config

    def _write_to_registry(self, registry_path: Path, new_config: Dict[str, Any]) -> None:
        """
        PROBLEM 3 RESOLUTION: Strictly atomic write protected against freezes
        from the IntelligentThermalPacer using os.replace().
        """
        try:
            # Safely ensure the parent directory exists
            registry_path.parent.mkdir(parents=True, exist_ok=True)
            
            if registry_path.exists() and registry_path.stat().st_size > 0:
                with open(registry_path, "r", encoding="utf-8") as r_file:
                    data = json.load(r_file)
            else:
                data = {"registered_patterns": []}
                
            # Deduplication by mathematical pattern ID
            existing_ids = {p["pattern_id"] for p in data["registered_patterns"]}
            if new_config["pattern_id"] not in existing_ids:
                data["registered_patterns"].append(new_config)
                
                # Atomic write via a temporary file on the same filesystem
                with tempfile.NamedTemporaryFile('w', dir=registry_path.parent, delete=False, suffix='.tmp', encoding='utf-8') as tf:
                    json.dump(data, tf, indent=2, ensure_ascii=False)
                    temp_path = tf.name
                    
                os.replace(temp_path, registry_path)
                
        except Exception as e:
            self.context.container.telemetry_ledger["errors_logged"] += 1
            raise RegistryWriteError(f"Atomic append operation failed on registry {registry_path}: {str(e)}")

```
