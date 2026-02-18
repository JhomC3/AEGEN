"""
Configuración del sistema de logging para MAGI.
Implementa las mejores prácticas de logging incluyendo:
- Rotación de archivos de log
- Formateo detallado de mensajes (texto y JSON)
- Configuración basada en diccionario
- Manejo de múltiples handlers
- Soporte para logs estructurados en JSON para producción
"""

import logging
import logging.config
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, cast

from src.core.logging.formatters import CorrelationIdFilter, JsonFormatter
from src.core.logging.types import LoggersConfig, LoggingDictConfiguration

from .config import settings

# Formatos
TEXT_FORMAT = (
    "%(asctime)s | %(correlation_id)s | %(name)-12s | %(levelname)-8s | "
    "%(filename)s:%(lineno)d | %(funcName)s | %(message)s"
)


def setup_logging() -> logging.Logger:
    """Configura el sistema de logging."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    is_production = settings.APP_ENV == settings.APP_ENV.PRODUCTION

    valid_log_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    log_level_setting = settings.LOG_LEVEL.upper()
    if log_level_setting not in valid_log_levels:
        effective_log_level = "INFO"
        logging.warning(
            f"Nivel de log inválido '{log_level_setting}' en configuración. "
            f"Usando nivel por defecto: {effective_log_level}"
        )
    else:
        effective_log_level = log_level_setting

    # Lista de loggers de terceros que se configurarán con un nivel WARNING
    # para reducir el ruido en los logs.
    third_party_loggers_to_silence = [
        "httpx",
        "google.generativeai",
        "fastapi",
        "sqlalchemy.engine",
        "pydantic",
    ]

    # Construcción dinámica de la configuración de loggers
    loggers_config: LoggersConfig = {
        # El logger raíz captura todo por defecto
        "": {
            "level": effective_log_level,
            "handlers": ["console", "file"],
            "propagate": True,
        },
        # Configuraciones específicas que no siguen el patrón común
        "uvicorn": {"level": "INFO", "handlers": ["console"], "propagate": False},
        "uvicorn.error": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
        "uvicorn.access": {
            "level": "WARNING" if is_production else "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
    }

    for logger_name in third_party_loggers_to_silence:
        loggers_config[logger_name] = {
            "level": "WARNING",
            "handlers": ["console", "file"],
            "propagate": False,
        }

    log_file = log_dir / f"MAGI_{settings.APP_ENV.value}.log"

    config: LoggingDictConfiguration = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "correlation_id": {
                "()": CorrelationIdFilter,
            },
        },
        "formatters": {
            "standard_text": {  # Coincide con StandardTextFormatterConfig
                "format": TEXT_FORMAT,
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "standard_json": {  # Coincide con dict[str, Any] dentro de FormatterEntry
                "()": JsonFormatter,
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {  # Coincide con dict[str, Any] dentro de HandlerEntry
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "standard_json" if is_production else "standard_text",
                "stream": sys.stdout,  # sys.stdout es TextIO
                "filters": ["correlation_id"],
            },
            "file": {  # Coincide con dict[str, Any] dentro de HandlerEntry
                "()": RotatingFileHandler,
                "level": "DEBUG",
                "formatter": "standard_json" if is_production else "standard_text",
                "filename": str(log_file),
                "maxBytes": 10485760,
                "backupCount": 5,
                "encoding": "utf8",
                "filters": ["correlation_id"],
            },
        },
        "loggers": loggers_config,
    }

    logging.config.dictConfig(cast(dict[str, Any], config))

    module_logger = logging.getLogger(__name__)
    module_logger.info(
        f"Sistema de logging configurado con nivel raíz: {effective_log_level}"
    )
    module_logger.info("Los logs de archivo se guardarán en: %s", log_file.resolve())
    module_logger.info("Entorno actual: %s", settings.APP_ENV.value)
    module_logger.info(
        "Formato de log en consola: %s", "JSON" if is_production else "Texto"
    )
    module_logger.info("Configuración de logging completada usando dictConfig.")

    return module_logger
