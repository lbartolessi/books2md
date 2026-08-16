"""A structural sanitization and multimedia asset extraction engine.

This package provides the MediaProcessor, a Stage 2 processor responsible for
purging embedded binary noise, organizing local media resources, and preparing
semantic multimedia pointers for downstream processing.
"""

from .processor import MediaProcessor

__all__ = ["MediaProcessor"]
