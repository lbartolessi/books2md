"""A test script to verify structural poetry patterns.

This script reads HTML snippets from 'Structural Patterns Test Bench.md',
processes each one through the PoetryNormalizer, and writes the input and output
to 'Structural Patterns Output.md' for visual verification.

It is designed to be run as a standalone script to generate the output file.
"""

import re
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from bs4.element import Tag
from markdownify import MarkdownConverter

from packages.dom_normalizer.src.dom_normalizer.core.config import EngineConfiguration
from packages.dom_normalizer.src.dom_normalizer.core.context import BookStyleContext
from packages.dom_normalizer.src.dom_normalizer.core.dom_utils import coerce_class_list
from packages.dom_normalizer.src.dom_normalizer.core.lang_codes import ISOLanguageCode
from packages.dom_normalizer.src.dom_normalizer.poetry.normalizer import (
    PoetryNormalizer,
)

# --- Constants ---
PROJECT_ROOT = Path(__file__).parent.parent.parent
TEST_BENCH_PATH = (
    PROJECT_ROOT / "tests" / "poetry" / "Structural Patterns Test Bench.md"
)


class PoetryMarkdownConverter(MarkdownConverter):
    """A custom MarkdownConverter to produce Pandoc's line blocks for poetry.

    This converter overrides the default `div` handling to identify a
    `<div class="line-block">` and transform its contents (a mix of text and
    <br> tags) into Pandoc's line block syntax (`| `).
    """

    def _reconstruct_lines_from_line_block(self, el: Tag) -> list[str]:
        """Reconstructs a list of text lines from a line-block div."""
        lines = []
        current_line_parts = []
        for content in el.contents:
            if isinstance(content, Tag) and content.name == "br":
                lines.append("".join(current_line_parts))
                current_line_parts = []
            else:
                # This handles both NavigableString and other Tags like <span>
                # by extracting their text content.
                current_line_parts.append(content.get_text())
        # Add the last line
        lines.append("".join(current_line_parts))
        return lines

    def convert_div(self, el: Tag, text: str, *args: Any, **_kwargs: Any) -> str:
        """Overrides the default div conversion to handle poetry blocks.

        If the element is a poetry block, it manually constructs the line block
        output. Otherwise, it falls back to the default div conversion.

        This method uses a flexible signature (*args, **kwargs) to handle
        inconsistent calling conventions within the markdownify library.

        Args:
            el: The BeautifulSoup element to convert.
            text: The already converted text content of the element.
            *args: Positional arguments from markdownify (may contain bool or set).
            **_kwargs: Unused keyword arguments from markdownify.

        Returns:
            The converted Markdown string.
        """
        # Handle inconsistent calling conventions in markdownify
        if args and isinstance(args[0], bool) and args[0]:
            return text  # Called with convert_as_inline=True

        if "line-block" in coerce_class_list(el.get("class")):
            lines = self._reconstruct_lines_from_line_block(el)
            # Format each reconstructed line with the Pandoc line block prefix.
            md_lines = [f"| {line}" for line in lines]
            return "\n".join(md_lines)

        # The traceback indicates the base `convert_div` method expects an
        # iterable `parent_tags` as its third argument. To work around the
        # library's inconsistent API where we might not have this, we pass an
        # empty set as a safe default for the fallback.
        return super().convert_div(el, text, set())  # type: ignore


def parse_test_bench(file_path: Path) -> list[dict[str, str]]:
    """Parses the structural patterns test bench markdown file.

    Args:
        file_path: The path to the markdown test bench file.

    Returns:
        A list of dictionaries, each containing the 'id' and 'html' of a test case.
    """
    content = file_path.read_text(encoding="utf-8")

    # Regex to find DOC_ID and the following html block
    pattern = re.compile(r"- DOC_ID: (.*?)\n\n\s*- ```html\n(.*?)\n\s*```", re.DOTALL)

    matches = pattern.findall(content)
    return [
        {"id": doc_id.strip(), "html": html_content.strip()}
        for doc_id, html_content in matches
    ]


def run_tests_and_generate_output() -> None:
    """Reads test cases, processes them, and writes the output to a markdown file."""
    # Setup paths relative to the project root
    test_bench_path = TEST_BENCH_PATH
    output_path = PROJECT_ROOT / "tests" / "poetry" / "Structural Patterns Output.md"

    # Parse test cases from the markdown file
    test_cases = parse_test_bench(test_bench_path)

    # Setup the normalizer with the correct registry
    config = EngineConfiguration(
        high_poetry_priority=True,
    )
    context = BookStyleContext(config=config, primary_language=ISOLanguageCode("en"))

    output_lines = ["# Structural Patterns Transformation Output\n\n"]

    for case in test_cases:
        # Re-initialize the normalizer for each case to ensure clean state
        normalizer = PoetryNormalizer(context)
        soup = BeautifulSoup(f"<body>{case['html']}</body>", "html.parser")

        # Process the soup
        output_soup, _ = normalizer.process(soup)

        output_lines.extend(
            [
                f"## DOC_ID: {case['id']}\n\n",
                "### Input\n",
                f"```html\n{case['html']}\n```\n\n",
                "### HTML Output\n",
                "```html\n",
            ],
        )
        if output_soup.body:
            output_lines.append(output_soup.body.prettify().strip())
        else:
            output_lines.append("<!-- ERROR: No body tag found in output soup -->")
        output_lines.append("\n```\n\n")

        output_lines.extend(["### Markdown Output\n", "```markdown\n"])
        if output_soup.body:
            converter = PoetryMarkdownConverter()
            md_output = converter.convert(str(output_soup.body))
            output_lines.append(md_output.strip())
        else:
            output_lines.append("<!-- ERROR: No body tag found in output soup -->")

        output_lines.extend(["\n```\n\n", "---\n\n"])

    output_path.write_text("".join(output_lines), encoding="utf-8")
    print(f"Output successfully generated at: {output_path}")


if __name__ == "__main__":
    run_tests_and_generate_output()
