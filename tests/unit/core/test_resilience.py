# tests/unit/core/test_resilience.py
from unittest.mock import AsyncMock, call

import pytest

from src.core.resilience import retry_on_failure


@pytest.mark.asyncio
async def test_retry_success_on_first_attempt():
    """
    Verifica que el decorador no interfiere si la función tiene éxito al primer intento.
    """
    # Crear un mock asíncrono que simula la función a decorar
    mock_func = AsyncMock(return_value="success")

    # Decorar la función mock
    decorated_func = retry_on_failure(retries=3, delay=0.1)(mock_func)

    # Ejecutar la función decorada
    result = await decorated_func("arg1", kwarg1="value1")

    # Verificar los resultados
    assert result == "success"
    mock_func.assert_awaited_once_with("arg1", kwarg1="value1")


@pytest.mark.asyncio
async def test_retry_succeeds_on_second_attempt():
    """
    Verifica que el decorador reintenta la función si falla la primera vez
    y tiene éxito en la segunda.
    """
    mock_func = AsyncMock(
        side_effect=[ValueError("Fallo inicial"), "Éxito en el reintento"]
    )

    decorated_func = retry_on_failure(retries=3, delay=0.1)(mock_func)

    result = await decorated_func()

    # El resultado final debe ser el de la ejecución exitosa
    assert result == "Éxito en el reintento"
    # La función debe haber sido llamada dos veces
    assert mock_func.await_count == 2


@pytest.mark.asyncio
async def test_retry_fails_after_all_attempts():
    """
    Verifica que el decorador levanta la excepción original después de
    agotar todos los reintentos.
    """
    mock_func = AsyncMock(
        side_effect=[
            ValueError("Fallo 1"),
            OSError("Fallo 2"),
            TypeError("Fallo final"),
        ]
    )
    retries = 3
    decorated_func = retry_on_failure(retries=retries, delay=0.1)(mock_func)

    # Verificar que la última excepción (TypeError) es la que se propaga
    with pytest.raises(TypeError, match="Fallo final"):
        await decorated_func()

    # Verificar que la función fue llamada exactamente el número de veces de los reintentos
    assert mock_func.await_count == retries


@pytest.mark.asyncio
async def test_retry_uses_correct_backoff_delay(mocker):
    """
    Verifica que el decorador aplica el delay y el backoff correctamente
    entre reintentos.
    """
    # Mockear asyncio.sleep para no esperar realmente y poder espiar sus llamadas
    mock_sleep = mocker.patch("asyncio.sleep", return_value=None)

    mock_func = AsyncMock(side_effect=ValueError("Fallo persistente"))

    decorated_func = retry_on_failure(retries=4, delay=0.5, backoff=2)(mock_func)

    with pytest.raises(ValueError):
        await decorated_func()

    # Verificar que se llamó a sleep con los delays correctos
    # Intento 1: falla, sleep(0.5)
    # Intento 2: falla, sleep(1.0)
    # Intento 3: falla, sleep(2.0)
    # Intento 4: falla, se rinde (no más sleep)
    expected_calls = [call(0.5), call(1.0), call(2.0)]
    mock_sleep.assert_has_calls(expected_calls)
    assert mock_sleep.call_count == 3
