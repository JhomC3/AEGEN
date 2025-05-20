from .base import BaseAppSettings


class ProdAppSettings(BaseAppSettings):
    LOG_LEVEL: str = "INFO"
    # Sobrescribir o añadir config específica de prod
    VECTOR_DB_URL: str | None = "http://prod-vector-db:8000"  # Ejemplo
