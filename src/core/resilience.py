"""Mecanismos de resiliencia como decoradores."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")

logger = logging.getLogger(__name__)


def retry_on_failure(
    retries: int = 3, delay: float = 1.0, backoff: float = 2.0
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """
    Decorador para reintentar una función asíncrona en caso de fallo.

    Args:
        retries: El número máximo de intentos.
        delay: El retraso inicial en segundos.
        backoff: El factor por el cual se multiplica el retraso en cada reintento.

    Returns:
        Un decorador que envuelve la función con lógica de reintentos.
    """

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            current_delay = delay
            for i in range(retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if i == retries - 1:
                        logger.error(
                            f"La función '{func.__name__}' falló después de {retries} intentos. Rindiéndose.",
                            exc_info=True,
                        )
                        raise
                    else:
                        logger.warning(
                            f"Intento {i + 1}/{retries} para '{func.__name__}' falló: {e}. "
                            f"Reintentando en {current_delay:.2f} segundos...",
                            exc_info=True,
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
            # Este punto no debería ser alcanzado teóricamente debido al `raise` en el bucle,
            # pero se incluye para satisfacer al type checker y por robustez.
            raise RuntimeError(
                f"La función '{func.__name__}' falló inesperadamente después de todos los reintentos."
            )

        return wrapper

    return decorator
