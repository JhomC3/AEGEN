from typing import Any, Literal, TypedDict
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class CanonicalEventV1(BaseModel):
    """
    Evento normalizado para entrada estándar en grafos.
    """

    event_id: UUID = Field(default_factory=uuid4, description="ID único del evento.")
    event_type: Literal["text", "audio", "document", "image", "unknown"] = Field(
        ..., description="Tipo lógico del contenido."
    )
    source: str = Field(..., description="Fuente (ej. 'telegram').")
    chat_id: int | str = Field(..., description="ID del chat de origen.")
    user_id: int | str | None = Field(None, description="ID del usuario de origen.")
    file_id: str | None = Field(None, description="ID del archivo.")
    content: Any | None = Field(None, description="Contenido principal.")
    timestamp: str | None = Field(None, description="Timestamp ISO.")
    first_name: str | None = Field(None, description="Nombre del usuario.")
    language_code: str | None = Field(None, description="Código de lenguaje.")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Metadatos adicionales."
    )

    model_config = {"extra": "allow"}


class V2ChatMessage(TypedDict, total=False):
    """Mensaje de chat Redis-safe."""

    role: Literal["user", "assistant", "system", "tool"]
    content: str
    timestamp: str | None
    message_length: int
    message_type: str | None
    agent_type: str | None
    delegation_used: bool
    processing_type: str | None


class GraphStateV2(TypedDict):
    """Versión 2 del estado del grafo."""

    event: CanonicalEventV1
    payload: dict[str, Any]
    error_message: str | None
    session_id: str
    conversation_history: list[V2ChatMessage]


class GenericMessageEvent(BaseModel):
    """Estructura de un evento de mensaje genérico."""

    task_id: str = Field(..., description="ID único de la tarea.")
    task_name: str = Field(..., description="Nombre de la tarea.")
    user_info: dict[str, Any] = Field(
        ..., description="Info (user_id, user_name, chat_id)."
    )
    message_type: str = Field(..., description="Tipo de mensaje.")
    content: Any = Field(..., description="Contenido principal.")
    file_name: str | None = Field(None, description="Nombre del archivo.")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Metadatos específicos."
    )
