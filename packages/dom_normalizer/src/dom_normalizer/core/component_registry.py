"""A central registry for dynamically creating processor components.

This module implements the Service Locator / Factory pattern to decouple the
test runner and main pipeline from the concrete implementation of processor
classes. Each processor module is responsible for registering a factory function
that knows how to instantiate it with its specific dependencies.
"""

from collections.abc import Callable
from typing import Any, TypeVar

# The factory takes a context and optional kwargs and returns a processor instance.
ProcessorFactory = Callable[..., Any]

PROCESSOR_FACTORIES: dict[str, ProcessorFactory] = {}

# Use a TypeVar to create a generic decorator that works for both functions and classes.
F = TypeVar("F", bound=Callable[..., Any])


def register_processor_factory(name: str) -> Callable[[F], F]:
    """A decorator to register a processor factory function or class in the global registry."""

    def decorator(factory: F) -> F:
        if name in PROCESSOR_FACTORIES:
            raise ValueError(f"Processor factory for '{name}' already registered.")
        PROCESSOR_FACTORIES[name] = factory
        return factory

    return decorator


def create_processor(name: str, context: Any, **kwargs: Any) -> Any:
    """Creates a processor instance using a registered factory."""
    try:
        factory = PROCESSOR_FACTORIES[name]
        return factory(context=context, **kwargs)
    except KeyError as e:
        raise ImportError(f"Processor factory for '{name}' not found. Available: {list(PROCESSOR_FACTORIES.keys())}") from e