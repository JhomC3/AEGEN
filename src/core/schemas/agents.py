from typing import Any

from pydantic import BaseModel, Field

from src.core.schemas.common import AgentResultStatus


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
