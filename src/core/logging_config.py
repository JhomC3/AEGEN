"""
Configuración del sistema de logging para AEGEN.
Implementa las mejores prácticas de logging incluyendo:
- Rotación de archivos de log
- Formateo detallado de mensajes (texto y JSON)
- Configuración basada en diccionario
- Manejo de múltiples handlers
- Soporte para logs estructurados en JSON para producción
"""

import json
import logging
import logging.config
import sys
from logging import LogRecord
from logging.handlers import RotatingFileHandler
from pathlib import Path

# TypedDict y Literal son necesarios. Any, TextIO también.
# List, Union, Dict de typing ya no son necesarios para Python 3.10+ en muchos casos.
from typing import (
    Any,
    Literal,
    TypeAlias,
    TypedDict,
    cast,
)

# Optional, Type (si se usan explícitamente)
from .config import settings
from .middleware import correlation_id

# --- Tipos para JSON --- # ruff: noqa: UP040
JsonValue: TypeAlias = str | int | float | bool | None | list[Any] | dict[str, Any]
JsonDict: TypeAlias = dict[str, JsonValue]

# Formatos
TEXT_FORMAT = "%(asctime)s | %(correlation_id)s | %(name)-12s | %(levelname)-8s | %(filename)s:%(lineno)d | %(funcName)s | %(message)s"
# JSON_FORMAT (el diccionario) no se usa directamente, JsonFormatter lo implementa.


class CorrelationIdFilter(logging.Filter):
    """Filtro para inyectar el correlation_id en los registros de log."""

    def filter(self, record: LogRecord) -> bool:
        """
        Añade el ID de correlación al registro.

        Args:
            record: El registro de log.

        Returns:
            True para indicar que el registro debe ser procesado.
        """
        record.correlation_id = correlation_id.get()
        return True


class JsonFormatter(logging.Formatter):
    """Formateador personalizado para logs en JSON."""

    _STANDARD_ATTRS = {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "message",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
        "correlation_id",  # Añadir para que no se duplique
    }

    def format(self, record: LogRecord) -> str:
        log_output: JsonDict = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", None),
            "filename": record.filename,
            "lineno": record.lineno,
            "function": record.funcName,
        }
        if record.exc_info:
            log_output["exc_info"] = self.formatException(record.exc_info)

        extra_data_val = getattr(record, "extra_data", None)
        if isinstance(extra_data_val, dict):
            # Ayuda a Pylance con el tipo de las claves
            typed_extra_data = cast(dict[str, Any], extra_data_val)
            for key, value in typed_extra_data.items():
                if key not in self._STANDARD_ATTRS and key not in log_output:
                    log_output[key] = value
        return json.dumps(log_output)


# --- TypedDicts para la configuración del logging ---


class StandardTextFormatterConfig(TypedDict):
    format: str
    datefmt: str


# Para formateadores y manejadores que usan claves especiales como "()" o "class",
# la entrada correspondiente en el diccionario de configuración se tipará como dict[str, Any].
FormatterEntry = StandardTextFormatterConfig | dict[str, Any]  # Usando | para Union
FormattersConfig = dict[str, FormatterEntry]

HandlerEntry = dict[str, Any]  # Esto cubre ConsoleHandler y FileHandler
HandlersConfig = dict[str, HandlerEntry]


class LoggerConfig(TypedDict):
    level: str
    handlers: list[str]  # Usando list incorporada
    propagate: bool


LoggersConfig = dict[str, LoggerConfig]


class LoggingDictConfiguration(TypedDict, total=False):
    version: Literal[1]
    disable_existing_loggers: bool
    filters: dict[str, Any]
    formatters: FormattersConfig
    handlers: HandlersConfig
    loggers: LoggersConfig


def setup_logging() -> logging.Logger:
    """Configura el sistema de logging usando una configuración basada en diccionario."""
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
        "uvicorn.error": {"level": "INFO", "handlers": ["console"], "propagate": False},
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

    log_file = log_dir / f"AEGEN_{settings.APP_ENV.value}.log"

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
                "()": JsonFormatter,  # type: ignore[assignment]
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
                "()": RotatingFileHandler,  # type: ignore[assignment]
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
    module_logger.info(f"Los logs de archivo se guardarán en: {log_file.resolve()}")
    module_logger.info(f"Entorno actual: {settings.APP_ENV.value}")
    module_logger.info(
        f"Formato de log en consola: {'JSON' if is_production else 'Texto'}"
    )
    module_logger.info("Configuración de logging completada usando dictConfig.")

    return module_logger
