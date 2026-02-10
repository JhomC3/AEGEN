from typing import Any, Literal, TypedDict
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class CanonicalEventV1(BaseModel):
    """
    Evento normalizado que sirve como entrada estándar para los grafos de agentes.
    Traduce un evento de una fuente externa (ej. Telegram, API) a un formato
    común que el sistema puede procesar de manera agnóstica a la fuente.
    (Versión 1)
    """

    event_id: UUID = Field(
        default_factory=uuid4, description="Identificador único del evento."
    )
    event_type: Literal["text", "audio", "document", "image", "unknown"] = Field(
        ..., description="Tipo lógico del contenido principal del evento."
    )
    source: str = Field(..., description="Fuente del evento (ej. 'telegram', 'api').")
    chat_id: int | str = Field(
        ..., description="Identificador del chat o sesión de origen."
    )
    user_id: int | str | None = Field(
        None, description="Identificador del usuario de origen."
    )
    file_id: str | None = Field(
        None, description="Identificador del archivo, si aplica."
    )
    content: Any | None = Field(
        None, description="Contenido principal del mensaje (ej. texto, URL)."
    )
    timestamp: str | None = Field(
        None, description="Timestamp del evento (ISO format)."
    )
    first_name: str | None = Field(
        None,
        description="Nombre de pila del usuario (si está disponible en la plataforma).",
    )
    language_code: str | None = Field(
        None, description="Código de lenguaje del usuario (ej. 'es-AR')."
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Metadatos adicionales de la fuente."
    )

    model_config = {"extra": "allow"}


class GraphStateV1(TypedDict):
    """
    Define el objeto de estado genérico que fluye a través de los grafos de LangGraph.
    Mantiene toda la información necesaria para el procesamiento de una solicitud.
    (Versión 1)
    # TODO: Evaluar eliminación - Reemplazado por V2
    """

    event: CanonicalEventV1
    payload: dict[str, Any]
    error_message: str | None


class V2ChatMessage(TypedDict, total=False):
    """
    Mensaje de chat Redis-safe, JSON-serializable para historial conversacional.
    Evita la complejidad de serialización de objetos LangChain BaseMessage.
    Usa total=False para permitir campos opcionales.
    """

    role: Literal["user", "assistant", "system", "tool"]
    content: str
    timestamp: str | None
    message_length: int
    message_type: str | None
    agent_type: str | None
    delegation_used: bool
    processing_type: str | None


class GraphStateV2(TypedDict):
    """
    Versión evolucionada del estado del grafo para flujos conversacionales.
    Incluye historial de conversación persistente para memoria entre turnos.
    (Versión 2 - Breaking change desde V1)

    Utiliza TypedDict para compatibilidad nativa con LangGraph.
    """

    event: CanonicalEventV1
    payload: dict[str, Any]
    error_message: str | None
    session_id: str  # ID de sesión para tracking y memoria
    # Nuevo campo para memoria conversacional
    conversation_history: list[V2ChatMessage]


class GenericMessageEvent(BaseModel):
    """
    Define la estructura de un evento de mensaje genérico que se publica en el bus.
    Actúa como un Data Transfer Object (DTO) para estandarizar la información
    de diferentes fuentes de ingesta (Telegram, API, etc.).
    """

    task_id: str = Field(..., description="Identificador único de la tarea.")
    task_name: str = Field(..., description="Nombre de la tarea a ejecutar.")
    user_info: dict[str, Any] = Field(
        ...,
        description="Información sobre el usuario y el chat (user_id, user_name, chat_id).",
    )
    message_type: str = Field(
        ..., description="Tipo de mensaje (ej. 'text', 'image', 'audio')."
    )
    content: Any = Field(
        ...,
        description="Contenido principal del mensaje (texto, objeto de archivo, etc.).",
    )
    file_name: str | None = Field(None, description="Nombre del archivo, si aplica.")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadatos adicionales específicos de la plataforma.",
    )
