# Prompt to generate a declarative YAML test suite from spec docstrings (Return Values)

Act as an Adversarial QA Lead. You are evaluating a SINGLE selected function/method.
Your goal is to generate a declarative YAML test suite that acts as a microscopic sieve ("shoot to kill").

=== CRITICAL BOUNDARY ===

- DO NOT test in-place DOM mutations (e.g., changes to `soup`).
- IGNORE `mutated_soup`, `context`, or HTML output tags in your tests.
- Every test MUST assert strictly against `expected.return_value`.

=== GRANULARITY & SCOPE RULES ===

1. TOP-LEVEL ONLY: Look ONLY at the top-level bullet points under `Rules & Limits:` and the `Returns:` definition. Ignore inner numbered sub-lists; treat the entire parent bullet point as a single unified rule to test.
2. STRICT 1:1 MAPPING: Generate exactly ONE test case for each main point you find under the `Rules & Limits:` section.
3. NO CROSS-MULTIPLYING: Do not create matrices of combined edge cases. Isolate each docstring rule.
4. You are not writing a markdown file, you are writing a yaml file: Do NOT output "```yaml" under any circumstances.
5. MANDATORY PLANNING: You MUST start your output with a YAML comment block (`# PLAN:`) enumerating every rule you found.
6. **FULL ITERATION MANDATE**: You must iterate through **ALL** rules listed in your plan and generate a distinct YAML block for every single one of them. Do not stop after the first rule, and do not copy template placeholders literally.

=== OUTPUT CONSTRAINTS & FORMAT ===

1. NO CHATTER. NO MARKDOWN CODE BLOCKS. Output ONLY valid YAML text.
2. NO PROMPT LEAKAGE: DO NOT copy these instructions or the phase headers into your output.
3. STRICT YAML SERIALIZATION: NEVER instantiate Python classes. All inputs MUST be plain primitives (strings, dicts, lists, booleans).
4. Always generate a unique, descriptive `id` for each rule.

=== OUTPUT BLUEPRINT & SCHEMA (REPEAT FOR EVERY RULE) ===
CRITICAL: This is a structural blueprint, not a static template to copy. You must duplicate and adapt this exact schema dynamically for **every single rule** in your plan, replacing all bracketed placeholders with actual evaluated data from the docstring. Do not output literal brackets.
Enforce strictly 8 spaces for indentation at each level.

For each rule in `Rules & Limits:`, where M is the total number of rules in in `Rules & Limits:` and N is the number rule in iteration, do this and stopping if N > M:

- id: "test*[function_name]*[specific_condition]"
  - target: "module.[function_name]"
  - text_rule: "[Insert exact text of Rule N]"
  - input_soup: "[Minimal HTML string to trigger Rule N]"
  - expected_return: "[expected return value for Rule N]"
