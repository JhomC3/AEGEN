"""
Paquete de schemas de AEGEN.
Este paquete centraliza todos los modelos Pydantic y TypedDict utilizados
en el sistema, organizados por dominios (API, Telegram, Grafo, Agentes, etc.).
Re-exporta todos los modelos para mantener compatibilidad con los imports existentes.
"""

from src.core.schemas.agents import (
    AgentContext,
    AgentResult,
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
    ServiceHealth,
    StatusResponse,
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
    UserRole,
)
from src.core.schemas.graph import (
    CanonicalEventV1,
    GenericMessageEvent,
    GraphStateV2,
    V2ChatMessage,
)
from src.core.schemas.profile import (
    ClinicalSafety,
    CopingMechanisms,
    CrisisContact,
    Evolution,
    Identity,
    Localization,
    MemorySettings,
    PersonalityAdaptation,
    ProfileMetadata,
    PsychologicalState,
    SupportPreferences,
    TasksAndActivities,
    TimelineEntry,
    UserProfile,
    ValuesAndGoals,
)
from src.core.schemas.session import ConversationSession
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
    "UserRole",
    "Permission",
    "AgentCapability",
    "AgentResultStatus",
    # API
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
    # Telegram
    "TelegramChat",
    "TelegramVoice",
    "TelegramPhoto",
    "TelegramUser",
    "TelegramMessage",
    "TelegramUpdate",
    # Graph
    "CanonicalEventV1",
    "GraphStateV2",
    "V2ChatMessage",
    "GenericMessageEvent",
    # Agents
    "AgentContext",
    "AgentResult",
    # Profile
    "ClinicalSafety",
    "CopingMechanisms",
    "CrisisContact",
    "Evolution",
    "Identity",
    "Localization",
    "MemorySettings",
    "PersonalityAdaptation",
    "ProfileMetadata",
    "PsychologicalState",
    "SupportPreferences",
    "TasksAndActivities",
    "TimelineEntry",
    "UserProfile",
    "ValuesAndGoals",
    # Session
    "ConversationSession",
]
