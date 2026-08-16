=== CONFIGURATION ===
TARGET_MODULE: "skeletons/dom_normalizer/structural_sanitizer/strategies.py"

Act as an Adversarial QA Lead and a deterministic rule-parser. Your primary task is to GENERATE A NEW FILE SPECIFICATION for the single module defined in `TARGET_MODULE`.

=== PHASE 1: TARGET PATH CALCULATION ===

1. Read the path in `TARGET_MODULE`.
2. Compute the new file target path by replacing `skeletons/` with `tests/specs/` and `.py` with `.yaml`.
   (e.g., `skeletons/dom_normalizer/table_normalizer.py` -> `tests/specs/dom_normalizer/table_normalizer.yaml`).
3. You MUST format the output as a code block with the exact target path declared on the first line inside the block, using the format: `# File: tests/specs/...`.

=== PHASE 2: DOCSTRING EXTRACTION & INHERITANCE RESOLUTION ===
Read the docstrings of the target Python module specified in `TARGET_MODULE`.

1. INHERITANCE RESOLUTION:
   - Check if the target class inherits from a base class (e.g., `BaseNormalizer` or similar in `skeletons/`).
   - For all concrete methods available in the target class (both defined locally and inherited):
     - If an inherited method is NOT overridden, inspect and extract the docstring from the base class in `skeletons/`.
     - If an inherited method IS overridden, use the subclass docstring.

2. DOCSTRING PARSING:
   - Locate the sections explicitly labeled as `Mutations:` and `Rules & Limits:`.
   - TOP-LEVEL ONLY: Evaluate ONLY top-level bullet points under `Mutations:` and `Rules & Limits:`. Treat each parent bullet point as a single unified rule to test.
   - STRICT 1:1 MAPPING: Generate exactly ONE test case for each top-level bullet point. Do not create matrices of combined edge cases.
   - MILLIMETRIC BOUNDARIES: If a rule defines a numeric limit, ratio, or threshold, test the exact boundary and one off-boundary case.

=== PHASE 3: YAML SCHEMA ALIGNMENT ===
Use the Universal Test Schema:

- package: "<module_name_in_snake_case>"
- dependencies: ["core"]
- pipeline_position: `<integer>`
- test_cases:
  - id: "UNIQUE_UPPERCASE_ID"
    target: "Method or specific behavior under test"
    description: "Brief explanation of the semantic rule being tested"
    context: # OPTIONAL
      is_code_block: true/false
      file_name: "document.xhtml"
    input:
      html: 'Input XHTML string'
    expected:
      html: 'Expected mutated XHTML'
      telemetry: # OPTIONAL
        metric_name: expected_value

=== PHASE 4: OUTPUT FORMAT (STRICT FILE CREATION TRIGGER) ===
Output ONLY a single yaml code block.
Inside the code block, line 1 MUST be: `# File: <calculated_tests_specs_path>`
Followed immediately by the raw YAML payload.
