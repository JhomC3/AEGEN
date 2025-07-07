from .base import BaseAppSettings


class ProductionSettings(BaseAppSettings):
    LOG_LEVEL: str = "INFO"
    APP_VERSION: str = "0.1.0"
    # Sobrescribir o añadir config específica de prod
    VECTOR_DB_URL: str | None = "http://prod-vector-db:8000"  # Ejemplo
