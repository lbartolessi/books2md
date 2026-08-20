from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class NormalizerStrategy(Protocol):
    """
    Protocolo que define la interfaz para las estrategias de normalización de elementos DOM.

    Las clases que implementen este protocolo deben proporcionar una lógica específica
    para transformar o limpiar un elemento dado.
    """

    def process(self, element: Any) -> Any:
        """
        Procesa un elemento y retorna su forma normalizada.

        Args:
            element (Any): El elemento DOM (o representación del mismo) a normalizar.

        Returns:
            Any: El elemento procesado o normalizado.
        """
        ...
