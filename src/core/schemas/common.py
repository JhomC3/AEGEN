from enum import Enum


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

    # TODO: Evaluar eliminación - sin consumidores activos externos detectados
    STAY_LOCAL = "STAY_LOCAL"
    MIGRATE_TO_DISTRIBUTED = "MIGRATE_TO_DISTRIBUTED"


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
