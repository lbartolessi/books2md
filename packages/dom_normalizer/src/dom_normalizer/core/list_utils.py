"""A collection of utility functions for list normalization logic.

This module centralizes complex helper logic for list prefix stripping to
reduce the cognitive load of the main ListNormalizer and make the core
list-reconstruction flow easier to follow.
"""

from __future__ import annotations

from bs4.element import NavigableString, PageElement, Tag

from .dom_utils import snapshot_iterator


def get_text_from_child(child: PageElement) -> str:
    """Gets the textual content of a child node for prefix matching.

    Args:
        child: The child node to process.

    Returns:
        The text content of the node, or an empty string for unknown types.

    Raises:
        None

    Mutations:
        None
    """
    if isinstance(child, NavigableString):
        return str(child)
    return child.get_text() if isinstance(child, Tag) else ""


def trim_text_from_tag_start(tag: Tag, length: int) -> None:
    r"""Surgically removes a specified number of characters from the start of a tag's visible text.

    This mutates the tag in-place by consuming text from its descendant text nodes
    in document order until the specified length is removed. This is a complex
    operation necessary to handle prefixes that are intertwined with inline
    formatting tags (e.g., `<p><b>1.</b> First item</p>`). Due to its
    complexity, this function requires careful maintenance and thorough testing
    against edge cases.

    The deep, recursive traversal (`find_all(string=True)`) is intentional, as
    it correctly handles cases where parts of the prefix are inside nested
    inline formatting tags.

    Args:
        tag: The tag to trim.
        length: The number of characters to remove from the start.

    Raises:
        None
    """
    to_consume = length
    # Use a tuple for a safe snapshot during DOM mutation.
    for text_node in snapshot_iterator(tag.find_all(string=True)):
        if to_consume <= 0:
            break
        tn_text = str(text_node)
        if len(tn_text) <= to_consume:
            # This entire text node is consumed.
            to_consume -= len(tn_text)
            text_node.extract()
        else:
            # Only part of this text node is consumed.
            new_tn_text = tn_text[to_consume:]
            text_node.replace_with(NavigableString(new_tn_text))
            to_consume = 0


def handle_partial_prefix_consumption(
    child: PageElement,
    prefix_to_consume: str,
) -> None:
    r"""Consumes a prefix from the start of a child node that is longer than the prefix.

    This handles the complex case where the prefix boundary falls inside a child node,
    either by slicing a text node or by recursively trimming a tag's content.

    Args:
        child: The node from which to consume the prefix.
        prefix_to_consume: The prefix string to remove.

    Raises:
        None

    Mutations:
        Modifies the `child` node in-place by removing the `prefix_to_consume`.
    """
    # Defensive guard: Ensure the child's text actually starts with the prefix
    # before attempting to consume it. This makes the function safer for reuse.
    if not get_text_from_child(child).startswith(prefix_to_consume):
        return

    consume_len = len(prefix_to_consume)
    if isinstance(child, NavigableString):
        # For a simple text node, slice the string.
        child_text = str(child)
        new_text = child_text[consume_len:]
        child.replace_with(NavigableString(new_text))
    elif isinstance(child, Tag):
        # For a tag, we need to surgically remove the prefix.
        trim_text_from_tag_start(child, consume_len)


def strip_prefix_from_tag(tag: Tag, prefix: str) -> None:
    """Removes a textual prefix from the start of a tag's content.

    This function robustly handles leading whitespace and nested inline tags.
    It first checks if the tag's text, after stripping leading whitespace,
    starts with the given prefix. If it does, it calculates the total number
    of characters to remove (including the whitespace) and surgically trims
    them from the start of the tag's descendant text nodes.

    Args:
        tag: The tag from which to strip the prefix.
        prefix: The textual prefix to remove.

    Raises:
        None

    Mutations:
        Modifies the `tag` in-place by removing the `prefix` and any leading
        whitespace from its content.
    """
    if not prefix:
        return

    tag_text = tag.get_text()
    stripped_text = tag_text.lstrip()
    if not stripped_text.startswith(prefix):
        return

    # Calculate the total number of characters to remove, including leading
    # whitespace and the prefix itself, then use the surgical trim helper.
    leading_whitespace_len = len(tag_text) - len(stripped_text)
    total_chars_to_remove = leading_whitespace_len + len(prefix)
    trim_text_from_tag_start(tag, total_chars_to_remove)
