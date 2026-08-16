# Prompt to generate a declarative YAML test suite from spec docstrings (DOM Mutations)

Act as an Adversarial QA Lead. You are evaluating a SINGLE selected function/method.
Your goal is to generate a declarative YAML test suite that acts as a microscopic sieve ("shoot to kill").

=== CRITICAL BOUNDARY ===
- DO NOT assert function return values, status codes, or telemetry dictionaries.
- Every test MUST assert the DOM modification strictly using `input.soup` -> `expected.mutated_soup` (and `mutated_context` if applicable).

=== PHASE 1: DOCSTRING EXTRACTION (NO GUESSING) ===
DO NOT attempt to infer or guess the rules from the Python logic.
Instead, read the docstring of the selected function.
Locate the lists explicitly labeled as `Mutations:` and `Rules & Limits:`.

=== GRANULARITY & SCOPE RULES ===
1. TOP-LEVEL ONLY: Look ONLY at the top-level bullet points under `Mutations:` and `Rules & Limits:`. Ignore inner numbered sub-lists; treat the entire parent bullet point as a single unified rule to test.
2. STRICT 1:1 MAPPING: Generate exactly ONE test case for each top-level bullet point found.
3. NO CROSS-MULTIPLYING: Do not create matrices of combined edge cases. Isolate each docstring rule.

=== SKILL: CROSS-MUTATION & CONTEXT MOCKING ===
TUTORIAL: How to handle functions that mutate secondary files or shared context.
When a docstring rule states that an action happens in the "donor file", "context", or "secondary node":
1. DO NOT inject the payload into the primary `soup`.
2. YOU MUST mock the secondary state inside the `context` input dictionary.
3. YOU MUST reflect the separated outcomes in the `expected` dictionary using distinct keys (`mutated_soup` vs `mutated_context`).

=== PHASE 2: IN-CONTEXT LEARNING (ICL) REFERENCE LIBRARY ===

Analyze the docstring and apply the correct structure.

--- PATTERN A: CROSS-MUTATION (DONOR FILES / SECONDARY STATE) ---
TRIGGER: The docstring states an action happens in a "donor file" or "context".

# ANALYSIS: Testing cross-mutation where a backlink is injected into a secondary context file.
# TARGET RULE: Injects a backlink <a> tag into the note body node found in the donor file.
- id: "test_inject_backlink_into_donor_file"
  target: "module.function"
  input:
    soup: "<body><a type=\"note\" xlink:href=\"#target_id\">Note</a></body>"
    context:
      donor_files:
        current: "<div id=\"target_id\"><p>Note body.</p></div>"
  expected:
    mutated_soup: "<body><a type=\"note\" xlink:href=\"#target_id\" id=\"fnref-target_id-1\">Note</a></body>"
    mutated_context:
      donor_files:
        current: "<div id=\"target_id\"><p>Note body.<a role=\"doc-backlink\" href=\"#fnref-target_id-1\"></a></p></div>"

--- PATTERN B: STANDARD DOM MUTATION ---
TRIGGER: The docstring states the primary DOM (`soup`) is modified in-place.

# ANALYSIS: Testing direct tag transformation and attribute annihilation.
# TARGET RULE: Transforms floating elements into <aside> tags while stripping class attributes.
- id: "test_transform_floating_div_to_aside"
  target: "module.process"
  input:
    soup: "<body><div class=\"floating-element\">Content</div></body>"
  expected:
    mutated_soup: "<body><aside>Content</aside></body>"

=== PHASE 3: OUTPUT CONSTRAINTS & FORMAT ===
1. REQUIREMENT: Before outputting the `# TARGET RULE` comment, you MUST write exactly ONE comment line explaining your structural choice.
   Write: `# ANALYSIS: Using pattern for [explain what the function mutates based on the docstring].`
2. NO CHATTER. NO MARKDOWN BLOCKS. Output ONLY the YAML.
3. Do not output global headers like `tests:` or ```yaml.
4. STRICT YAML SERIALIZATION: NEVER instantiate Python classes. All DOM states MUST be plain text HTML strings.
5. Always generate a unique, descriptive `id` for each rule. DO NOT copy example IDs.
