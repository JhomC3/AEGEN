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
    APP_VERSION: str = "0.1.1"
    LOG_LEVEL: str = "INFO"

    # Secretos
    GOOGLE_API_KEY: SecretStr | None = None
    OPENROUTER_API_KEY: SecretStr | None = None  # New for OpenRouter
    GROQ_API_KEY: SecretStr | None = None

    # LLM Provider Configuration
    LLM_PROVIDER: str = "groq"  # Options: "groq", "google", "openrouter"
    OPENROUTER_MODEL_NAME: str = "openai/gpt-oss-120b:free"
    GROQ_MODEL_NAME: str = "moonshotai/kimi-k2-instruct-0905"
    GROQ_BACKUP_MODEL_NAME: str = "gpt-oss-120"
    ALCHEMY_API_KEY: SecretStr | None = None

    # === LLM Models por Tarea ===
    # Chat Principal y Razonamiento
    CHAT_MODEL: str = "moonshotai/kimi-k2-instruct-0905"
    CHAT_FALLBACK_MODEL: str = "gpt-oss-120"
    REASONING_MODEL: str = "moonshotai/kimi-k2-instruct-0905"

    # Audio (Groq Whisper)
    AUDIO_MODEL: str = "whisper-large-v3-turbo"

    # RAG (Gemini por ventana de contexto y File API)
    RAG_MODEL: str = "gemini-2.5-flash-lite"

    # Routing y Default
    ROUTING_MODEL: str = "moonshotai/kimi-k2-instruct-0905"
    DEFAULT_LLM_MODEL: str = "moonshotai/kimi-k2-instruct-0905"

    ETHERSCAN_API_KEY: SecretStr | None = None
    TAVILY_API_KEY: SecretStr | None = None
    CHROMA_API_KEY: SecretStr | None = None
    YOUTUBE_API_KEY: SecretStr | None = None
    TELEGRAM_BOT_TOKEN: SecretStr | None = None
    NGROK_AUTHTOKEN: SecretStr | None = None

    # SQLite Configuration
    SQLITE_DB_PATH: str = "data/aegen_memory.db"
    SQLITE_SCHEMA_PATH: str = "src/memory/schema.sql"

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

    # Umbrales para el MigrationDecisionEngine
    CPU_THRESHOLD_PERCENT: float = 80.0
    MEMORY_THRESHOLD_PERCENT: float = 80.0

    # Rutas de recursos
    PROMPTS_DIR: str = "src/prompts"

    # --- Validación ---
    # Validar que claves esenciales existan en producción
    @model_validator(mode="after")
    def validate_production_secrets(self):
        env = self.APP_ENV
        if env == Environment.PRODUCTION:
            required_secrets = ["GOOGLE_API_KEY"]
            missing = [k for k in required_secrets if not getattr(self, k)]
            if missing:
                raise ValueError(
                    f"Missing required production settings: {', '.join(missing)}"
                )
        return self
