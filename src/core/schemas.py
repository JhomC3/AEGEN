# src/core/schemas.py
from enum import Enum
from typing import Any, Literal, TypedDict
from uuid import UUID, uuid4

from pydantic import (
    BaseModel,
    Field,
)

# --- Enumeraciones Comunes ---


class AppEnvironment(str, Enum):
    """Enumeración para los entornos de la aplicación."""

    LOCAL = "local"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class AnalysisStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPLETED_STUB = "completed_stub"  # Para stubs iniciales


class ReportFormat(str, Enum):
    TEXT_SUMMARY = "text_summary"
    JSON_DETAILED = "json_detailed"
    MARKDOWN_REPORT = "markdown_report"


class HealthStatus(str, Enum):
    """Enumeración para el estado general de salud de la aplicación."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ServiceStatus(str, Enum):
    """Enumeración para el estado de un servicio individual."""

    OK = "ok"
    PENDING = "pending"
    ERROR = "error"
    DEGRADED = "degraded"


class SystemState(str, Enum):
    """Enum para representar el estado recomendado del sistema."""

    STAY_LOCAL = "STAY_LOCAL"
    MIGRATE_TO_DISTRIBUTED = "MIGRATE_TO_DISTRIBUTED"


# --- Esquemas del Sistema ---


class SystemStatus(BaseModel):
    """Modelo de datos para el estado del sistema."""

    cpu_usage_percent: float
    memory_usage_percent: float
    state: SystemState
    message: str


# --- Esquemas para Solicitudes API ---
class AnalyzeQuery(BaseModel):
    query: str = Field(
        ...,
        min_length=5,
        max_length=1000,
        description="The user's request or question for analysis.",
        examples=[
            "Analyze the sentiment towards the new Optimism upgrade on Twitter this week."
        ],
    )
    user_id: str | None = Field(
        None, description="Optional user identifier.", examples=["user-123"]
    )
    session_id: UUID | None = Field(
        None,
        description="Optional session identifier for tracking.",
        examples=[uuid4()],
    )
    # Podrías añadir más campos como filtros, rango de fechas, etc.
    # report_format: ReportFormat = Field(default=ReportFormat.TEXT_SUMMARY, description="Desired format for the report.")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "What are the main risks associated with the EigenLayer restaking protocol?",
                    "user_id": "dev-user-001",
                }
            ]
        }
    }


# --- Esquemas para Respuestas API ---
class StatusResponse(BaseModel):
    status: str = Field(..., examples=["MAGI API is running!"])
    environment: AppEnvironment = Field(
        ...,
        description="Current running environment (local, dev, prod).",
        examples=[AppEnvironment.DEVELOPMENT],
    )
    version: str = Field(..., description="API version.", examples=["0.1.0"])


class ServiceHealth(BaseModel):
    name: str = Field(..., description="Name of the service dependency.")
    status: ServiceStatus = Field(
        ...,
        description="Status of the service ('ok', 'degraded', 'error').",
        examples=[ServiceStatus.OK],
    )
    details: str | None = Field(
        None,
        description="Additional details about the service status.",
        examples=["Connected successfully"],
    )


class HealthCheckResponse(BaseModel):
    status: HealthStatus = Field(
        ...,
        description="Overall health status of the application.",
        examples=[HealthStatus.HEALTHY],
    )
    environment: AppEnvironment = Field(
        ...,
        description="Current running environment (local, dev, prod).",
        examples=[AppEnvironment.PRODUCTION],
    )
    services: list[ServiceHealth] = Field(
        default_factory=list, description="Status of critical dependent services."
    )


class AnalysisFinding(BaseModel):
    """Representa un hallazgo o insight específico del análisis."""

    id: UUID = Field(default_factory=uuid4)
    description: str = Field(..., description="Textual description of the finding.")
    severity: str | None = Field(
        None,
        description="Severity of the finding (e.g., high, medium, low).",
        examples=["high"],
    )
    confidence: float | None = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Confidence score for the finding (0.0 to 1.0).",
        examples=[0.85],
    )
    source_ids: list[str] = Field(
        default_factory=list,
        description="Identifiers of data sources related to this finding.",
    )
    metadata: dict[str, Any] | None = Field(
        None, description="Any additional metadata."
    )


class AnalysisDetails(BaseModel):
    """Estructura detallada para los resultados del análisis."""

    summary: str = Field(
        default="No summary available.",
        description="A concise summary of the entire analysis.",
    )
    key_findings: list[AnalysisFinding] = Field(
        default_factory=list,
        description="A list of specific, actionable insights or findings.",
    )
    data_sources_used: list[str] = Field(
        default_factory=list,
        description="List of data sources consulted for the analysis.",
        examples=[["Etherscan API", "TheGraph Subgraph XYZ", "Twitter API"]],
    )
    # Podrías añadir más campos como:
    # raw_data_summary: Optional[Dict[str, Any]] = None
    # potential_biases: List[str] = Field(default_factory=list)
    # error_messages: List[str] = Field(default_factory=list)


class AnalyzeResponse(BaseModel):
    """Respuesta final del endpoint de análisis."""

    request_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this analysis request.",
    )
    status: AnalysisStatus = Field(
        default=AnalysisStatus.COMPLETED,
        description="Overall status of the analysis process.",
    )
    query_received: str = Field(
        ..., description="The original query received from the user."
    )
    report_generated_at: str = Field(
        ...,
        description="Timestamp when the report was generated (ISO format).",
        examples=["2024-05-16T10:30:00Z"],
    )
    # report_format: ReportFormat = Field(..., description="Format of the main report content.")
    report_content: str = Field(
        ..., description="The main textual report generated by the Presenter Agent."
    )
    details: AnalysisDetails = Field(
        ..., description="Structured details and key findings of the analysis."
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "request_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
                    "status": "completed",
                    "query_received": "What are the main risks associated with the EigenLayer restaking protocol?",
                    "report_generated_at": "2024-05-16T11:00:00Z",
                    "report_content": "EigenLayer presents several risks including smart contract vulnerabilities, slashing risks, and potential oracle manipulation. Operator collusion is also a concern...",
                    "details": {
                        "summary": "Multiple risk vectors identified for EigenLayer, primarily around smart contract security and economic incentives.",
                        "key_findings": [
                            {
                                "id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
                                "description": "High risk of smart contract bugs due to complexity.",
                                "severity": "high",
                                "confidence": 0.9,
                                "source_ids": ["audit_report_X", "research_paper_Y"],
                            }
                        ],
                        "data_sources_used": [
                            "Security Audit Reports",
                            "Academic Papers",
                            "Community Discussions",
                        ],
                    },
                }
            ]
        }
    }


class IngestionResponse(BaseModel):
    """Respuesta para el endpoint de ingestión no bloqueante."""

    task_id: str = Field(..., description="Unique identifier for the accepted task.")
    message: str = Field(
        default="Request accepted for processing.",
        description="Confirms that the request has been accepted.",
    )


# --- Esquemas Internos (Ejemplos, si los agentes necesitan estructuras bien definidas) ---
class PlanStep(BaseModel):
    """Representa un paso en el plan de análisis."""

    step_id: int
    action: str = Field(..., description="Description of the action to perform.")
    tool_to_use: str | None = Field(None, description="Specific tool to be invoked.")
    tool_parameters: dict[str, Any] | None = Field(
        None, description="Parameters for the tool."
    )
    expected_output_description: str


class AnalysisPlan(BaseModel):
    """Representa el plan de análisis generado por el Planificador."""

    plan_id: UUID = Field(default_factory=uuid4)
    original_query: str
    steps: list[PlanStep]
    # report_format_requested: ReportFormat # Para que el Presentador sepa cómo formatear


class ReportGenerationState(BaseModel):
    """
    Define el estado para el pipeline de generación de reportes de video.
    Maneja el procesamiento de múltiples videos.
    """

    original_query: str

    # Lista de diccionarios, cada uno con info de un video
    videos_to_process: list[dict[str, Any]] = Field(default_factory=list)

    # Listas para mantener los resultados de cada video
    transcripts: list[str] = Field(default_factory=list)
    audio_file_paths: list[str] = Field(default_factory=list)

    # El reporte final combinado
    report: str = Field(default="")
    error: str | None = Field(default=None)


# --- Esquemas para Procesamiento de Documentos ---


class DocumentContent(BaseModel):
    """Define la estructura de un resultado de procesamiento de documento exitoso."""

    type: Literal["document"] = "document"
    file_name: str = Field(..., description="El nombre original del archivo procesado.")
    content: str = Field(
        ..., description="El contenido de texto extraído del documento."
    )
    extension: str = Field(..., description="La extensión del archivo, ej: '.pdf'.")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "type": "document",
                    "file_name": "annual_report.docx",
                    "content": "This is the first paragraph...",
                    "extension": ".docx",
                }
            ]
        }
    }


class DocumentError(BaseModel):
    """Define la estructura para un error durante el procesamiento de un documento."""

    type: Literal["error"] = "error"
    file_name: str = Field(
        ..., description="El nombre del archivo que falló al procesar."
    )
    message: str = Field(..., description="El mensaje de error detallado.")
    extension: str = Field(
        ..., description="La extensión del archivo que causó el error."
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "type": "error",
                    "file_name": "corrupt.pdf",
                    "message": "El archivo PDF está corrupto o no se puede leer.",
                    "extension": ".pdf",
                }
            ]
        }
    }


# --- Esquemas para Eventos Internos ---


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


# --- Esquemas para Webhooks ---


class TelegramChat(BaseModel):
    id: int


class TelegramVoice(BaseModel):
    file_id: str


class TelegramPhoto(BaseModel):
    file_id: str
    width: int
    height: int


class TelegramUser(BaseModel):
    id: int
    is_bot: bool
    first_name: str
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None


class TelegramMessage(BaseModel):
    chat: TelegramChat
    from_user: TelegramUser | None = Field(None, alias="from")
    voice: TelegramVoice | None = None
    text: str | None = None
    photo: list[TelegramPhoto] | None = None
    caption: str | None = None


class TelegramUpdate(BaseModel):
    """
    Modela la estructura de una actualización entrante de un webhook de Telegram.
    Se enfoca específicamente en capturar mensajes de voz.
    """

    update_id: int
    message: TelegramMessage | None = None


# --- Esquemas para el Grafo de LangChain ---


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

    Utiliza TypedDict para compatibilidad nativa con LangGraph.
    """

    event: CanonicalEventV1
    payload: dict[str, Any]
    error_message: str | None


# --- Esquemas para Fase 3B: Memoria Conversacional ---


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


# --- Contratos JSON para Comunicación Inter-Componente (ADR-0006) ---


class InternalDelegationRequest(BaseModel):
    """
    Contrato para delegación interna de ChatAgent a especialistas.
    Define el formato estándar para comunicación inter-agente.
    """

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


# --- Sistema de Roles y Permisos (Fase 3C) ---


class UserRole(str, Enum):
    """Roles disponibles en el sistema multi-tenant."""

    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class Permission(str, Enum):
    """Permisos específicos para control de acceso."""

    READ_OWN = "read_own"
    WRITE_OWN = "write_own"
    READ_GLOBAL = "read_global"
    WRITE_GLOBAL = "write_global"
    MANAGE_USERS = "manage_users"


# --- Contratos para Agentes Modulares (Fase 3C) ---


class AgentCapability(str, Enum):
    """Capacidades estándar que puede tener un agente modular."""

    FILE_PROCESSING = "file_processing"
    NLP_ANALYSIS = "nlp_analysis"
    DATA_TRANSFORMATION = "data_transformation"
    CONTENT_GENERATION = "content_generation"
    MEMORY_MANAGEMENT = "memory_management"
    VALIDATION = "validation"


class AgentResultStatus(str, Enum):
    """Estados posibles del resultado de ejecución de un agente."""

    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    ERROR = "error"


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
