"""
Paquete de schemas de AEGEN.
Este paquete centraliza todos los modelos Pydantic y TypedDict utilizados
en el sistema, organizados por dominios (API, Telegram, Grafo, Agentes, etc.).
Re-exporta todos los modelos para mantener compatibilidad con los imports existentes.
"""

from src.core.schemas.agents import (
    AgentContext,
    AgentResult,
    InternalDelegationRequest,
    InternalDelegationResponse,
    TaskContext,
)
from src.core.schemas.api import (
    AnalysisDetails,
    AnalysisFinding,
    AnalysisPlan,
    AnalyzeQuery,
    AnalyzeResponse,
    HealthCheckResponse,
    IngestionResponse,
    PlanStep,
    ReportGenerationState,
    ServiceHealth,
    StatusResponse,
    SystemStatus,
)
from src.core.schemas.common import (
    AgentCapability,
    AgentResultStatus,
    AnalysisStatus,
    AppEnvironment,
    HealthStatus,
    Permission,
    ReportFormat,
    ServiceStatus,
    SystemState,
    UserRole,
)
from src.core.schemas.documents import (
    DocumentContent,
    DocumentError,
)
from src.core.schemas.graph import (
    CanonicalEventV1,
    GenericMessageEvent,
    GraphStateV1,
    GraphStateV2,
    V2ChatMessage,
)
from src.core.schemas.telegram import (
    TelegramChat,
    TelegramMessage,
    TelegramPhoto,
    TelegramUpdate,
    TelegramUser,
    TelegramVoice,
)

# Re-exportar todo para compatibilidad con 'from src.core.schemas import *'
__all__ = [
    # Common
    "AppEnvironment",
    "AnalysisStatus",
    "ReportFormat",
    "HealthStatus",
    "ServiceStatus",
    "SystemState",
    "UserRole",
    "Permission",
    "AgentCapability",
    "AgentResultStatus",
    # API
    "SystemStatus",
    "AnalyzeQuery",
    "StatusResponse",
    "ServiceHealth",
    "HealthCheckResponse",
    "AnalysisFinding",
    "AnalysisDetails",
    "AnalyzeResponse",
    "IngestionResponse",
    "PlanStep",
    "AnalysisPlan",
    "ReportGenerationState",
    # Telegram
    "TelegramChat",
    "TelegramVoice",
    "TelegramPhoto",
    "TelegramUser",
    "TelegramMessage",
    "TelegramUpdate",
    # Graph
    "CanonicalEventV1",
    "GraphStateV1",
    "GraphStateV2",
    "V2ChatMessage",
    "GenericMessageEvent",
    # Agents
    "InternalDelegationRequest",
    "InternalDelegationResponse",
    "TaskContext",
    "AgentContext",
    "AgentResult",
    # Documents
    "DocumentContent",
    "DocumentError",
]
