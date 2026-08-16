# Part 1: The "Universal" Test Schema (YAML)

To make every module fit the exact same mold, we only need to define a **superset of optional properties** in our test case structure. This is the definitive blueprint:

```yaml
test_cases:
  - id: TEST_ID
    target: "Method or specific behavior under test"
    description: "Brief explanation of the semantic rule being tested"
    context:  # Optional: Environment configuration
      is_code_block: false  # Allows simulating the code block immunity shield
      file_name: "document.xhtml"  # For rules based on specific filenames
      book_base_name: "test_book"  # For media extraction paths
    input:
      html: 'Input XHTML string'
    expected:
      html: 'Expected mutated XHTML'
      telemetry:  # Optional: Verification of processor metrics
        metric_name: value
      files_written:  # Optional: Only for media_processor (disk writes)
        - path: "file/path/to/verify"
          content_hash: "expected_hash_or_content"

```

## Examples of Direct Module Adaptation

### 1. `heading_normalizer` (Suites 1, 2, and 3)

```yaml
package: heading_normalizer
dependencies: ["core"]
pipeline_position: 4
test_cases:
  - id: HEAD_001
    target: "Pass 1: Completely Empty Heading"
    description: "An h1 with no content must be downgraded to a paragraph with an empty b tag."
    input:
      html: '<body><h1></h1><p>Normal text.</p></body>'
    expected:
      html: '<body><p><b></b></p><p>Normal text.</p></body>'

  - id: HEAD_002
    target: "Pass 2: Simple Hierarchical Jump"
    description: "A jump from h1 to h3 must be repaired by downgrading the h3 to h2."
    input:
      html: '<body><h1>Level 1</h1><h3>Invalid Level 3</h3></body>'
    expected:
      html: '<body><h1>Level 1</h1><h2>Invalid Level 3</h2></body>'

  - id: HEAD_003
    target: "Suite 3: Protected Document (Code Block)"
    description: "If the document is marked as a code block, the normalizer must remain idle."
    context:
      is_code_block: true
    input:
      html: '<body data-is-code-block="true"><h1>Title</h1><h3>Invalid Jump</h3></body>'
    expected:
      html: '<body data-is-code-block="true"><h1>Title</h1><h3>Invalid Jump</h3></body>'

```

### 2. `table_normalizer` (Cases A and B)

```yaml
package: table_normalizer
dependencies: ["core"]
pipeline_position: 5
test_cases:
  - id: TAB_001
    target: "Suite 1: Simple and Valid Div Grid"
    description: "Div layout classes converted to a table with a tbody."
    input:
      html: '<body><div class="table-like"><div class="row"><div class="cell">Header 1</div></div></div></body>'
    expected:
      html: '<body><table class="table-like table-block"><tbody><tr class="row"><th>Header 1</th></tr></tbody></table>'

  - id: TAB_002
    target: "Suite 3: Fusion of Tables Separated by Noise"
    description: "Consolidate tables with matching column signatures separated by pagination noise."
    input:
      html: '<body><table><tr><td>A1</td><td>B1</td></tr></table><br/><div class="page-break"></div><table><tr><td>A2</td><td>B2</td></tr></table></body>'
    expected:
      html: '<body><table><tbody><tr><td>A1</td><td>B1</td></tr><tr><td>A2</td><td>B2</td></tr></tbody></table></body>'

```

### 3. `media_processor` (Handling Side Effects)

```yaml
package: media_processor
dependencies: ["core"]
pipeline_position: 7
test_cases:
  - id: MED_001
    target: "Layer A: Base64 Image Extraction"
    description: "Extract inline Base64 src into a relative asset file."
    context:
      book_base_name: "test_book"
    input:
      html: '<body><img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="></body>'
    expected:
      html: '<body><img src="test_book/extracted/asset_12345.png"></body>'
      files_written:
        - path: "test_book/extracted/asset_12345.png"
          content_hash: "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

```


