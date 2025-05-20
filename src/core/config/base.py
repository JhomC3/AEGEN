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

    APP_NAME: str = "OnChainIQ"
    APP_ENV: Environment = APP_ENV  # Carga la variable de entorno
    LOG_LEVEL: str = "INFO"

    # Secretos
    GEMINI_API_KEY: SecretStr | None = None
    ALCHEMY_API_KEY: SecretStr | None = None
    ETHERSCAN_API_KEY: SecretStr | None = None
    # ... otros secretos

    # Conexiones
    REDIS_URL: str = "redis://localhost:6379/0"

    # Configs generales
    DEFAULT_LLM_MODEL: str = "gemini-2.5-flash-preview-04-17"
    DEFAULT_TEMPERATURE: float = 0.7
    VECTOR_DB_PATH: str | None = None  # Ej: para ChromaDB local
    VECTOR_DB_URL: str | None = None  # Ej: para instancia remota

    # --- Validación ---
    # Validar que claves esenciales existan en producción
    @model_validator(mode="after")
    def validate_production_secrets(self):
        env = self.APP_ENV
        if env == Environment.PRODUCTION:
            required_secrets = ["GEMINI_API_KEY"]
            missing = [k for k in required_secrets if not getattr(self, k)]
            if missing:
                raise ValueError(
                    f"Missing required production settings: {', '.join(missing)}"
                )
        return self
