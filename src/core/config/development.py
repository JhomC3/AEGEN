from .base import BaseAppSettings


class DevAppSettings(BaseAppSettings):
    LOG_LEVEL: str = "DEBUG"
    # Sobrescribir o añadir config específica de dev
    VECTOR_DB_PATH: str = "./chromadb_dev_data"
