from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class AnalyzerProtocol(Protocol):
    """Protocolo base para analizadores de estructuras DOM.

    Define la interfaz estándar para clases encargadas de extraer información
    o detectar patrones semánticos en el árbol DOM.
    """

    def analyze(self, dom: Any) -> Any:
        """Analiza la estructura del DOM para extraer metadatos o identificar patrones.

        Args:
            dom: El nodo o estructura del DOM a analizar.

        Returns:
            El resultado del análisis, que puede incluir metadatos, banderas
            de estado o estructuras de datos extraídas.
        """
        ...
