# src/core/interfaces/tool.py
from abc import ABC, abstractmethod
from typing import Any


class ITool(ABC):
    """
    Define la interfaz para una herramienta que puede ser utilizada por los workflows.

    Las herramientas encapsulan una funcionalidad específica y reutilizable, como
    llamar a una API externa, procesar un archivo o realizar un cálculo complejo.
    """

    name: str
    description: str

    @abstractmethod
    async def arun(self, **kwargs: Any) -> Any:
        """
        Ejecuta la herramienta de forma asíncrona.

        Args:
            **kwargs: Argumentos dinámicos que la herramienta necesita para operar.
                      Esto proporciona flexibilidad para diferentes tipos de herramientas.

        Returns:
            El resultado de la ejecución de la herramienta.
        """
        pass
