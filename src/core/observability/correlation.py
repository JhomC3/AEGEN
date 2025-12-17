# src/core/observability/correlation.py
"""
Gestión de correlation IDs para trazabilidad end-to-end.
Responsabilidad única: Interfaz unificada con middleware existente.
"""

import uuid

# Importar ContextVar existente del middleware
from src.core.middleware import correlation_id as correlation_id_var


def get_correlation_id() -> str:
    """
    Obtiene el correlation ID actual o crea uno nuevo.

    Returns:
        str: Correlation ID único para el request actual
    """
    try:
        current_id = correlation_id_var.get()
        if current_id:
            return current_id
    except LookupError:
        pass

    # Crear nuevo ID si no existe
    new_id = str(uuid.uuid4())
    correlation_id_var.set(new_id)
    return new_id


def set_correlation_id(correlation_id: str) -> None:
    """
    Establece el correlation ID en el contexto actual.

    Args:
        correlation_id: ID a establecer en el contexto
    """
    correlation_id_var.set(correlation_id)
