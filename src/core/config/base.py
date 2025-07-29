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
    APP_VERSION: str = "0.1.0"
    LOG_LEVEL: str = "INFO"

    # Secretos
    GOOGLE_API_KEY: SecretStr | None = None
    ALCHEMY_API_KEY: SecretStr | None = None
    ETHERSCAN_API_KEY: SecretStr | None = None
    TAVILY_API_KEY: SecretStr | None = None
    CHROMA_API_KEY: SecretStr | None = None
    YOUTUBE_API_KEY: SecretStr | None = None
    TELEGRAM_BOT_TOKEN: SecretStr | None = None
    # ... otros secretos

    # Conexiones
    REDIS_URL: str = "redis://localhost:6379/0"

    # Configs generales
    DEFAULT_LLM_MODEL: str = "google_genai:gemini-2.5-flash"
    DEFAULT_TEMPERATURE: float = 0.7
    DEFAULT_WHISPER_MODEL: str = "base"
    VECTOR_DB_PATH: str | None = None  # Ej: para ChromaDB local
    VECTOR_DB_URL: str | None = None  # Ej: para instancia remota
    DEBUG_MODE: bool = False
    ALLOWED_HOSTS: list[str] = ["*"]

    # Umbrales para el MigrationDecisionEngine
    CPU_THRESHOLD_PERCENT: float = 80.0
    MEMORY_THRESHOLD_PERCENT: float = 80.0

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
