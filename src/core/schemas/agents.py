from typing import Any, Literal

from pydantic import BaseModel, Field

from src.core.schemas.common import AgentResultStatus
from src.core.schemas.graph import V2ChatMessage


class InternalDelegationRequest(BaseModel):
    """
    Contrato para delegación interna de ChatAgent a especialistas.
    Define el formato estándar para comunicación inter-agente.
    """

    # TODO: Evaluar eliminación - sin consumidores activos externos detectados

    task_type: Literal[
        "planning", "analysis", "transcription", "document_processing"
    ] = Field(..., description="Tipo de tarea a delegar al especialista")
    user_message: str = Field(..., description="Mensaje original del usuario")
    context: dict[str, Any] = Field(
        default_factory=dict, description="Contexto adicional para la tarea"
    )
    conversation_history: list[V2ChatMessage] = Field(
        default_factory=list, description="Historial conversacional relevante"
    )
    priority: Literal["low", "medium", "high", "urgent"] = Field(
        default="medium", description="Prioridad de la tarea"
    )


class InternalDelegationResponse(BaseModel):
    """
    Contrato para respuesta de especialistas a ChatAgent.
    Formato estándar para resultados que deben traducirse a lenguaje natural.
    """

    # TODO: Evaluar eliminación - sin consumidores activos externos detectados

    status: Literal["success", "error", "partial"] = Field(
        ..., description="Estado de la ejecución de la tarea"
    )
    result: dict[str, Any] = Field(
        default_factory=dict, description="Resultado estructurado de la tarea"
    )
    summary: str = Field(..., description="Resumen legible del resultado")
    suggestions: list[str] = Field(
        default_factory=list, description="Sugerencias para el usuario"
    )
    error_details: str | None = Field(
        None, description="Detalles del error si status=error"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Metadatos adicionales del procesamiento"
    )


class TaskContext(BaseModel):
    """
    Contexto compartido para flujo de datos entre componentes.
    Facilita el paso de información entre especialistas en chains complejos.
    """

    # TODO: Evaluar eliminación - sin consumidores activos externos detectados

    session_id: str = Field(..., description="ID de sesión para tracking del flujo")
    user_id: str = Field(..., description="ID del usuario para personalización")
    current_step: str = Field(
        ..., description="Paso actual en el flujo de procesamiento"
    )
    previous_results: dict[str, Any] = Field(
        default_factory=dict, description="Resultados de pasos anteriores"
    )
    shared_state: dict[str, Any] = Field(
        default_factory=dict, description="Estado compartido entre componentes"
    )
    preferences: dict[str, Any] = Field(
        default_factory=dict, description="Preferencias del usuario"
    )


class AgentContext(BaseModel):
    """
    Contexto de ejecución compartido entre agentes modulares.
    Contiene información necesaria para la ejecución y coordinación.
    """

    user_id: str = Field(..., description="ID único del usuario")
    session_id: str | None = Field(None, description="ID de sesión opcional")
    request_id: str | None = Field(None, description="ID de request para tracking")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Metadata adicional"
    )
    previous_results: list[dict[str, Any]] = Field(
        default_factory=list, description="Resultados de agentes anteriores"
    )

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Obtiene metadata específica con valor por defecto."""
        return self.metadata.get(key, default)


class AgentResult(BaseModel):
    """
    Resultado estandarizado de la ejecución de un agente modular.
    Proporciona información estructurada sobre el resultado y próximos pasos.
    """

    status: AgentResultStatus = Field(..., description="Estado del resultado")
    data: Any = Field(..., description="Datos resultado de la ejecución")
    message: str | None = Field(None, description="Mensaje descriptivo opcional")
    error_details: str | None = Field(None, description="Detalles del error si aplica")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Metadata del resultado"
    )
    next_suggested_agents: list[str] = Field(
        default_factory=list, description="Agentes sugeridos para siguiente paso"
    )

    @property
    def is_success(self) -> bool:
        """Indica si la ejecución fue exitosa (completa o parcial)."""
        return self.status in [
            AgentResultStatus.SUCCESS,
            AgentResultStatus.PARTIAL_SUCCESS,
        ]

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Obtiene metadata específica con valor por defecto."""
        return self.metadata.get(key, default)
