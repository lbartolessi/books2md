from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class StrategyProtocol(Protocol):
    """Protocolo base para estrategias de normalización de componentes DOM.

    Define la interfaz estándar para clases que realizan transformaciones
    específicas sobre fragmentos del árbol DOM.
    """

    def normalize(self, dom: Any) -> Any:
        """Aplica las reglas de normalización sobre el elemento o sub-árbol proporcionado.

        Args:
            dom: El nodo o estructura del DOM a normalizar.

        Returns:
            El nodo o estructura normalizada tras el procesamiento.
        """
        ...
