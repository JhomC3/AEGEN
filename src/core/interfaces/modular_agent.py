# src/core/interfaces/modular_agent.py
from abc import ABC, abstractmethod
from typing import Any, Protocol

from src.core.schemas import AgentCapability, AgentContext, AgentResult


class BaseModularAgent(Protocol):
    """Interface estable para agentes modulares componibles."""

    @abstractmethod
    async def execute(self, input_data: Any, context: AgentContext) -> AgentResult:
        """Ejecuta la lógica principal del agente."""
        pass

    @abstractmethod
    def get_capabilities(self) -> list[AgentCapability]:
        """Retorna las capacidades que ofrece este agente."""
        pass

    @abstractmethod
    def can_handle(self, task_type: str, input_data: Any = None) -> bool:
        """Determina si puede manejar un tipo de tarea específico."""
        pass


class ModularAgentBase(ABC):
    """Clase base opcional para implementaciones de BaseModularAgent."""

    def __init__(self, name: str, capabilities: list[AgentCapability]):
        self.name = name
        self._capabilities = capabilities

    def get_capabilities(self) -> list[AgentCapability]:
        """Retorna capacidades configuradas."""
        return self._capabilities.copy()

    def can_handle(self, task_type: str, input_data: Any = None) -> bool:
        """Mapea task_type a capabilities configuradas."""
        # Mapeo básico task_type -> capability
        capability_mapping = {
            "file_upload": AgentCapability.FILE_PROCESSING,
            "file_parse": AgentCapability.FILE_PROCESSING,
            "text_analysis": AgentCapability.NLP_ANALYSIS,
            "intent_detection": AgentCapability.NLP_ANALYSIS,
            "data_transform": AgentCapability.DATA_TRANSFORMATION,
            "content_generate": AgentCapability.CONTENT_GENERATION,
            "memory_store": AgentCapability.MEMORY_MANAGEMENT,
            "validate_input": AgentCapability.VALIDATION,
        }

        required_capability = capability_mapping.get(task_type)
        return required_capability in self._capabilities if required_capability else False

    @abstractmethod
    async def execute(self, input_data: Any, context: AgentContext) -> AgentResult:
        """Implementa lógica específica del agente."""
        pass

    def _create_success_result(
        self,
        data: Any,
        message: str | None = None,
        next_agents: list[str] | None = None
    ) -> AgentResult:
        """Crea resultado exitoso."""
        return AgentResult(
            status="success",
            data=data,
            message=message,
            next_suggested_agents=next_agents or []
        )

    def _create_error_result(
        self,
        error_message: str,
        error_details: str | None = None
    ) -> AgentResult:
        """Crea resultado de error."""
        return AgentResult(
            status="error",
            data=None,
            message=error_message,
            error_details=error_details
        )
