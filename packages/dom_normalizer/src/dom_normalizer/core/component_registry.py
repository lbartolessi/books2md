"""A central registry for dynamically creating processor components.

This module implements the Service Locator / Factory pattern to decouple the
test runner and main pipeline from the concrete implementation of processor
classes. Each processor module is responsible for registering a factory function
that knows how to instantiate it with its specific dependencies.
"""

from collections.abc import Callable
from typing import Any, TypeVar

from dom_normalizer.core.protocols import NormalizerStrategy

# The factory takes a context and optional kwargs and returns a processor instance.
ProcessorFactory = Callable[..., Any]

_PROCESSOR_FACTORIES: dict[str, ProcessorFactory] = {}

# Use a TypeVar to create a generic decorator that works for both functions and classes.
F = TypeVar("F", bound=Callable[..., Any])

def register_processor_factory(
    name: str,
    factory_func: ProcessorFactory | None = None,
):
    """Registers a factory and also supports decorator usage."""

    if factory_func is not None:
        _PROCESSOR_FACTORIES[name] = factory_func

    def decorator(component):
        _PROCESSOR_FACTORIES[name] = factory_func or component
        return component

    return decorator


def get_processor_factory(name: str) -> ProcessorFactory:
    try:
        return _PROCESSOR_FACTORIES[name]
    except KeyError as exc:
        raise KeyError(f"No processor factory registered for: {name}") from exc

class ComponentRegistry:
    def init(self) -> None: self._registry: dict[str, type[NormalizerStrategy]] = {}


    def register(self, tag_name: str, strategy_class: type[NormalizerStrategy]) -> None:
        """
        Registra una nueva estrategia de normalización para una etiqueta específica.
        """
        self._registry[tag_name] = strategy_class

    def get_strategy(self, tag_name: str) -> type[NormalizerStrategy]:
        """
        Obtiene la clase de estrategia registrada para una etiqueta específica.
        """
        if tag_name not in self._registry:
            raise KeyError(f"No strategy registered for tag: {tag_name}")
        return self._registry[tag_name]

    def has_strategy(self, tag_name: str) -> bool:
        """
        Verifica si existe una estrategia registrada para la etiqueta.
        """
        return tag_name in self._registry

    def list_registered_components(self) -> list[str]:
        """
        Retorna una lista de todas las etiquetas con estrategias registradas.
        """
        return list(self._registry.keys())
