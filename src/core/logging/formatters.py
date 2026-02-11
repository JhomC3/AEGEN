import json
import logging
from logging import LogRecord
from typing import Any, cast

from src.core.logging.types import JsonDict
from src.core.middleware import correlation_id


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
