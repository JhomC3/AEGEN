from .base import BaseAppSettings


class DevelopmentSettings(BaseAppSettings):
    LOG_LEVEL: str = "DEBUG"
    APP_VERSION: str = "0.1.0"
    # Sobrescribir o añadir config específica de dev
    VECTOR_DB_PATH: str | None = "./chromadb_dev_data"
