from dotenv import find_dotenv
from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .environments import APP_ENV, Environment  # Importar entorno


class BaseAppSettings(BaseSettings):
    # Configuración común a todos los entornos
    model_config = SettingsConfigDict(
        # Busca .env subiendo en el árbol de directorios
        env_file=find_dotenv(".env") or ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "AEGEN"
    APP_ENV: Environment = APP_ENV  # Carga la variable de entorno
    APP_VERSION: str = "0.7.2"  # Verificación de sincronización
    LOG_LEVEL: str = "INFO"

    # Secretos
    GOOGLE_API_KEY: SecretStr | None = None
    OPENROUTER_API_KEY: SecretStr | None = None  # New for OpenRouter
    GROQ_API_KEY: SecretStr | None = None

    # Configuración de Modelos (Mayo 2026)
    LLM_PROVIDER: str = "groq"
    OPENROUTER_MODEL_NAME: str = "minimax/minimax-m2.5:free"
    GROQ_MODEL_NAME: str = "openai/gpt-oss-120b"
    GROQ_BACKUP_MODEL_NAME: str = "llama3-70b-8192"  # Fallback adicional en groq

    # Administrador del sistema
    ADMIN_CHAT_ID: str | None = None

    # === LLM Models por Tarea ===
    # Chat Principal y Ruteo (Latencia ultra-baja)
    CHAT_MODEL: str = "openai/gpt-oss-120b"
    CHAT_FALLBACK_MODEL: str = "minimax/minimax-m2.5:free"

    # Razonamiento Analítico (Alta calidad)
    REASONING_MODEL: str = "minimax/minimax-m2.5:free"

    # Audio (Groq Whisper)
    AUDIO_MODEL: str = "whisper-large-v3-turbo"

    # RAG (Gemini por ventana de contexto y File API)
    RAG_MODEL: str = "gemini-2.5-flash"

    # Routing y Default
    ROUTING_MODEL: str = "openai/gpt-oss-120b"
    DEFAULT_LLM_MODEL: str = "openai/gpt-oss-120b"

    ETHERSCAN_API_KEY: SecretStr | None = None
    TAVILY_API_KEY: SecretStr | None = None
    CHROMA_API_KEY: SecretStr | None = None
    YOUTUBE_API_KEY: SecretStr | None = None
    TELEGRAM_BOT_TOKEN: SecretStr | None = None
    NGROK_AUTHTOKEN: SecretStr | None = None

    # Configuración de SQLite
    SQLITE_DB_PATH: str = "storage/aegen_memory.db"
    SQLITE_SCHEMA_PATH: str = "src/memory/schema.sql"
    SQLITE_BACKUP_DIR: str = "storage/backups"

    # Cloud Backup (GCS)
    GCS_BACKUP_BUCKET: str | None = None
    GCS_CREDENTIALS_JSON: SecretStr | None = None

    # LangSmith Configuration
    # El proyecto en LangSmith se mantiene como MAGI para trazabilidad o se cambia?
    # Lo cambiaremos a AEGEN para consistencia.
    LANGCHAIN_API_KEY: SecretStr | None = None
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_PROJECT: str = "AEGEN"

    # ... otros secretos

    # Conexiones
    REDIS_URL: str = "redis://redis:6379/0"
    REDIS_SESSION_URL: str = "redis://redis:6379/1"
    REDIS_SESSION_TTL: int = 3600  # 1 hour session timeout

    # Configs generales
    DEFAULT_TEMPERATURE: float = 0.3
    DEFAULT_WHISPER_MODEL: str = "small"
    DEBUG_MODE: bool = False
    ALLOWED_HOSTS: list[str] = ["*"]
    MESSAGE_DEBOUNCE_SECONDS: float = 1.2

    # Umbrales para el MigrationDecisionEngine
    CPU_THRESHOLD_PERCENT: float = 80.0
    MEMORY_THRESHOLD_PERCENT: float = 80.0

    # Rutas de recursos
    PROMPTS_DIR: str = "src/prompts"

    # --- Validación ---
    # Validar que claves esenciales existan en producción
    @model_validator(mode="after")
    def validate_production_secrets(self) -> "BaseAppSettings":
        env = self.APP_ENV
        if env == Environment.PRODUCTION:
            required_secrets = ["GOOGLE_API_KEY"]
            missing = [k for k in required_secrets if not getattr(self, k)]
            if missing:
                raise ValueError(
                    f"Missing required production settings: {', '.join(missing)}"
                )
        return self
