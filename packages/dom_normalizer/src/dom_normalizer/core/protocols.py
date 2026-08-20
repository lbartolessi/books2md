from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class NormalizerStrategy(Protocol):
    """Protocolo base para estrategias de normalización de DOM.

    Define la interfaz mínima que debe implementar cualquier estrategia
    encargada de transformar un nodo específico del árbol DOM.
    """

    def match(self, element: Any) -> bool:
        """Determina si la estrategia es aplicable al nodo proporcionado.

        Args:
            element: El nodo del DOM a evaluar.

        Returns:
            bool: True si la estrategia puede procesar el elemento, False en caso contrario.
        """
        ...

    def process(self, element: Any) -> Any:
        """Ejecuta la lógica de normalización sobre el nodo.

        Args:
            element: El nodo del DOM que será transformado.

        Returns:
            El nodo resultante tras la normalización.

        Raises:
            NotImplementedError: Si la lógica de transformación no está definida.
        """
        ...
