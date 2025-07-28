# src/core/schemas.py
from enum import Enum
from typing import Any, Literal
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
    status: str = Field(..., examples=["AEGEN API is running!"])
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
