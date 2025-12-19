# src/core/exceptions.py
from typing import Any


class AppBaseError(Exception):
    """Base exception para la aplicación MAGI."""

    def __init__(self, message: str, status_code: int = 500, detail: Any = None):
        self.message = message
        self.status_code = status_code
        self.detail = detail or message  # FastAPI usa 'detail'
        super().__init__(self.message)


class AgentError(AppBaseError):
    """Error específico relacionado con la operación de un agente."""

    def __init__(
        self,
        message: str = "Agent operation failed",
        agent_name: str = "UnknownAgent",
        detail: Any = None,
    ):
        super().__init__(message, status_code=500, detail=detail or message)
        self.agent_name = agent_name


class AgentConfigurationError(AgentError):
    """Error durante la configuración o inicialización de un agente."""

    def __init__(
        self,
        message: str = "Agent configuration error",
        agent_name: str = "UnknownAgent",
    ):
        super().__init__(message, agent_name=agent_name)  # 503 Service Unavailable


class DataAcquisitionError(AppBaseError):
    """Error durante la adquisición de datos de fuentes externas."""

    def __init__(
        self,
        message: str = "Failed to acquire data",
        source_name: str = "UnknownSource",
    ):
        super().__init__(message, status_code=502, detail=message)  # 502 Bad Gateway
        self.source_name = source_name


class LLMConnectionError(AppBaseError):
    """Error al conectar o interactuar con el LLM."""

    def __init__(self, message: str = "LLM interaction failed"):
        super().__init__(
            message, status_code=504, detail=message
        )  # 504 Gateway Timeout


class VectorDBError(AppBaseError):
    """Error al interactuar con la base de datos vectorial."""

    def __init__(self, message: str = "VectorDB operation failed"):
        super().__init__(message, status_code=503, detail=message)


# Puedes añadir más excepciones específicas según necesites.
