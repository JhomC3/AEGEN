# src/core/interfaces/specialist.py
from abc import ABC, abstractmethod
from typing import Any

from langchain_core.tools import BaseTool


class SpecialistInterface(ABC):
    """
    Define el contrato que todo agente especialista debe cumplir.
    Un especialista encapsula una capacidad de negocio específica,
    expone sus herramientas y define su propio flujo de trabajo interno (grafo).
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """El nombre único del especialista, usado para enrutamiento."""
        pass

    @property
    @abstractmethod
    def graph(self) -> Any:
        """El grafo de LangGraph compilado que define el flujo de trabajo del especialista."""
        pass

    @property
    @abstractmethod
    def tool(self) -> BaseTool:
        """La herramienta principal que expone la capacidad del especialista al orquestador."""
        pass

    @abstractmethod
    def get_capabilities(self) -> list[str]:
        """
        Devuelve una lista de los tipos de eventos que este especialista puede manejar.
        Ejemplos: ["audio", "text", "document:pdf", "image:jpg"]
        """
        pass
