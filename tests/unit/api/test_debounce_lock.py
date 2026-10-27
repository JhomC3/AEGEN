"""Regresiones del cerrojo de procesamiento por chat (spec 002, RF-5..RF-7)."""

import asyncio
import logging
import time
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.api.services import (
    debounce_manager,
    event_processor,
    lock_wait,
    processing_lock,
    startup_recovery,
)
from src.core import dependencies
from src.core.ingestion_buffer import IngestionBuffer

LOCK_KEY = "lock:processing:1"


def _fragment(content: str) -> dict[str, Any]:
    return {
        "event_type": "text",
        "content": content,
        "file_id": None,
        "language_code": "es",
        "first_name": "Test",
    }


class FakeRedis:
    """Redis mínimo con TTL, SET NX, listas y los scripts Lua del debounce."""

    def __init__(self) -> None:
        self.values: dict[str, Any] = {}
        self.expiries: dict[str, float] = {}
        self.set_calls: list[dict[str, Any]] = []
        self.eval_calls: list[tuple[str, str, str]] = []

    def _purge(self, key: str) -> None:
        expiry = self.expiries.get(key)
        if expiry is not None and time.monotonic() >= expiry:
            self.values.pop(key, None)
            self.expiries.pop(key, None)

    async def get(self, key: str) -> Any:
        self._purge(key)
        return self.values.get(key)

    async def set(
        self,
        key: str,
        value: Any,
        nx: bool = False,
        ex: float | None = None,
    ) -> bool | None:
        self._purge(key)
        self.set_calls.append({"key": key, "value": value, "nx": nx, "ex": ex})
        if nx and key in self.values:
            return None
        self.values[key] = value
        if ex is not None:
            self.expiries[key] = time.monotonic() + ex
        return True

    async def delete(self, key: str) -> int:
        self.expiries.pop(key, None)
        return 1 if self.values.pop(key, None) is not None else 0

    async def rpush(self, key: str, value: Any) -> int:
        self._purge(key)
        current = self.values.get(key)
        if not isinstance(current, list):
            current = []
            self.values[key] = current
        current.append(value)
        return len(current)

    async def lrange(self, key: str, start: int, end: int) -> list[Any]:
        self._purge(key)
        current = self.values.get(key)
        if not isinstance(current, list):
            return []
        return current[start:] if end == -1 else current[start : end + 1]

    async def incr(self, key: str) -> int:
        self._purge(key)
        value = int(self.values.get(key, 0)) + 1
        self.values[key] = value
        return value

    async def expire(self, key: str, seconds: float) -> bool:
        self._purge(key)
        if key not in self.values:
            return False
        self.expiries[key] = time.monotonic() + float(seconds)
        return True

    async def scan_iter(self, match: str | None = None) -> AsyncIterator[str]:
        prefix = match.removesuffix("*") if match else ""
        for key in list(self.values):
            self._purge(key)
            if key in self.values and key.startswith(prefix):
                yield key

    async def eval(self, script: str, _numkeys: int, key: str, *args: Any) -> int:
        self._purge(key)
        if script == processing_lock.RELEASE_LOCK_SCRIPT:
            token = str(args[0])
            self.eval_calls.append(("release", key, token))
            if self.values.get(key) == token:
                self.values.pop(key, None)
                self.expiries.pop(key, None)
                return 1
            return 0
        if script == processing_lock.RENEW_LOCK_SCRIPT:
            token = str(args[0])
            ttl = float(args[1])
            self.eval_calls.append(("renew", key, token))
            if self.values.get(key) == token:
                self.expiries[key] = time.monotonic() + ttl
                return 1
            return 0
        raise AssertionError(f"script inesperado: {script}")


class FakeBuffer:
    """Buffer con lotes pendientes; cada flush consume el siguiente lote."""

    def __init__(self, contents: list[str] | None = None) -> None:
        self.batches: list[list[dict[str, Any]]] = [
            [_fragment(content)] for content in (contents or ["hola"])
        ]
        self.sequence = 1
        self.flush_calls = 0
        self.ttl_refreshes = 0

    async def add(self, content: str) -> None:
        self.batches.append([_fragment(content)])
        self.sequence += 1

    async def refresh_ttl(self, _chat_id: str) -> None:
        self.ttl_refreshes += 1

    async def get_current_sequence(self, _chat_id: str) -> int:
        return self.sequence

    async def ensure_sequence(self, _chat_id: str) -> int:
        return self.sequence

    async def list_pending_chats(self) -> list[int]:
        return [1] if self.batches else []

    async def flush_all(self, _chat_id: str) -> list[dict[str, Any]]:
        self.flush_calls += 1
        return self.batches.pop(0) if self.batches else []


@pytest.fixture
def entorno(monkeypatch: pytest.MonkeyPatch) -> tuple[FakeRedis, FakeBuffer, list]:
    redis = FakeRedis()
    buffer = FakeBuffer()
    processed: list[str] = []

    monkeypatch.setattr(debounce_manager.settings, "MESSAGE_DEBOUNCE_SECONDS", 0.0)
    monkeypatch.setattr(debounce_manager, "ingestion_buffer", buffer)
    monkeypatch.setattr(processing_lock, "ingestion_buffer", buffer)
    monkeypatch.setattr(startup_recovery, "ingestion_buffer", buffer)
    monkeypatch.setattr(dependencies, "redis_connection", redis)
    monkeypatch.setattr(
        debounce_manager.telegram_interface.telegram_manager,
        "send_chat_action",
        AsyncMock(return_value=True),
    )

    async def fake_process(event: Any) -> None:
        processed.append(str(event.content))

    monkeypatch.setattr(debounce_manager, "process_event_task", fake_process)
    return redis, buffer, processed


@pytest.fixture(autouse=True)
async def _cancelar_reintentos_pendientes():
    lock_wait._shutting_down = False
    yield
    await lock_wait.cancel_pending_lock_retries()
    await startup_recovery.cancel_startup_recovery_tasks()


@pytest.mark.asyncio
async def test_cerrojo_adquirido_es_atomico_y_se_libera(
    entorno: tuple[FakeRedis, FakeBuffer, list],
) -> None:
    redis, buffer, _ = entorno

    await debounce_manager.process_buffered_events(1, 1, "trace")

    assert buffer.flush_calls == 1
    assert redis.set_calls, "debe adquirir el cerrojo con SET NX EX"
    assert redis.set_calls[0]["nx"] is True
    assert redis.set_calls[0]["ex"] == 60
    assert LOCK_KEY not in redis.values
    assert any(llamada[0] == "release" for llamada in redis.eval_calls)


@pytest.mark.asyncio
async def test_rafaga_durante_procesamiento_se_atiende_despues(
    entorno: tuple[FakeRedis, FakeBuffer, list],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """La segunda ráfaga espera y termina llegando a la ruta de respuesta.

    Con el comportamiento anterior (devolver si el cerrojo está ocupado) esta
    prueba falla en ``processed == ["hola", "segundo"]``: la segunda ráfaga se
    perdía.
    """
    redis, buffer, processed = entorno
    started = asyncio.Event()
    release = asyncio.Event()

    async def fake_process(event: Any) -> None:
        processed.append(str(event.content))
        started.set()
        await release.wait()

    monkeypatch.setattr(debounce_manager, "process_event_task", fake_process)

    first = asyncio.create_task(debounce_manager.process_buffered_events(1, 1, "t1"))
    await asyncio.wait_for(started.wait(), timeout=1)

    await buffer.add("segundo")
    second = asyncio.create_task(debounce_manager.process_buffered_events(1, 2, "t2"))
    await asyncio.sleep(0.1)

    # Mientras la primera procesa, la segunda no consume ni responde.
    assert processed == ["hola"]
    assert buffer.flush_calls == 1

    release.set()
    await asyncio.wait_for(asyncio.gather(first, second), timeout=5)

    # La segunda ráfaga no se descartó: se procesó después y llegó a respuesta.
    assert processed == ["hola", "segundo"]
    assert buffer.flush_calls == 2
    assert LOCK_KEY not in redis.values


@pytest.mark.asyncio
async def test_rafaga_durante_procesamiento_llega_a_telegram(
    entorno: tuple[FakeRedis, FakeBuffer, list],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prueba de extremo a extremo del debounce: dos respuestas reales.

    Usa el ``process_event_task`` real y solo mockea sus dependencias externas
    (orquestador, sesión y memoria). La segunda ráfaga debe terminar enviando
    su respuesta a Telegram, no solo quedar en el buffer.
    """
    _redis, buffer, _ = entorno
    sent: list[tuple[str, str]] = []
    started = asyncio.Event()
    release = asyncio.Event()

    def record_send(chat_id: str, message: str) -> bool:
        sent.append((chat_id, message))
        return True

    manager = MagicMock()
    manager.send_message = AsyncMock(side_effect=record_send)
    manager.send_chat_action = AsyncMock(return_value=True)
    monkeypatch.setattr(
        debounce_manager.telegram_interface,
        "get_telegram_manager",
        lambda: manager,
    )
    monkeypatch.setattr(event_processor, "_update_user_context", AsyncMock())
    monkeypatch.setattr(
        event_processor, "_load_session_context", AsyncMock(return_value=({}, []))
    )

    async def fake_run(event: Any, _payload: Any, _history: Any, _task_id: str) -> dict:
        if event.content == "hola":
            started.set()
            await release.wait()
        return {"payload": {"response": f"eco:{event.content}"}}

    monkeypatch.setattr(event_processor, "_run_orchestration", fake_run)
    monkeypatch.setattr(
        event_processor,
        "session_manager",
        MagicMock(save_session=AsyncMock()),
    )
    monkeypatch.setattr(event_processor, "_buffer_memory", AsyncMock())
    monkeypatch.setattr(
        debounce_manager, "process_event_task", event_processor.process_event_task
    )

    first = asyncio.create_task(debounce_manager.process_buffered_events(1, 1, "t1"))
    await asyncio.wait_for(started.wait(), timeout=1)

    await buffer.add("segundo")
    second = asyncio.create_task(debounce_manager.process_buffered_events(1, 2, "t2"))
    await asyncio.sleep(0.1)
    assert sent == []

    release.set()
    await asyncio.wait_for(asyncio.gather(first, second), timeout=5)

    assert sent == [("1", "eco:hola"), ("1", "eco:segundo")]


@pytest.mark.asyncio
async def test_renovacion_evita_procesamiento_simultaneo_al_expirar_ttl(
    entorno: tuple[FakeRedis, FakeBuffer, list],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Con TTL=1 s, el latido mantiene el cerrojo y evita solapamiento.

    Sin renovación, a los 1.0 s el cerrojo expira y la segunda tarea entra
    mientras la primera sigue activa; ``max_active`` sería 2.
    """
    _redis, buffer, processed = entorno
    monkeypatch.setattr(processing_lock, "PROCESSING_LOCK_TTL_SECONDS", 1)
    monkeypatch.setattr(
        processing_lock, "LOCK_RENEW_INTERVAL_SECONDS", 0.2, raising=False
    )
    monkeypatch.setattr(lock_wait, "LOCK_RETRY_INTERVAL_SECONDS", 0.05, raising=False)

    active = 0
    max_active = 0

    async def fake_process(event: Any) -> None:
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        processed.append(str(event.content))
        await asyncio.sleep(1.3)
        active -= 1

    monkeypatch.setattr(debounce_manager, "process_event_task", fake_process)

    first = asyncio.create_task(debounce_manager.process_buffered_events(1, 1, "t1"))
    await asyncio.sleep(0.3)
    await buffer.add("segundo")
    second = asyncio.create_task(debounce_manager.process_buffered_events(1, 2, "t2"))

    await asyncio.wait_for(asyncio.gather(first, second), timeout=6)

    assert processed == ["hola", "segundo"]
    assert max_active == 1, "el mismo chat no debe procesarse dos veces a la vez"


@pytest.mark.asyncio
async def test_cerrojo_ajeno_no_se_borra(
    entorno: tuple[FakeRedis, FakeBuffer, list],
) -> None:
    redis, _buffer, _ = entorno
    redis.values[LOCK_KEY] = "otra-tarea"

    await processing_lock.release_processing_lock(1, "token-propio")

    assert redis.values[LOCK_KEY] == "otra-tarea"


@pytest.mark.asyncio
async def test_espera_cerrojo_ajeno_y_procesa_al_liberarse(
    entorno: tuple[FakeRedis, FakeBuffer, list],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis, buffer, processed = entorno
    redis.values[LOCK_KEY] = "otra-tarea"
    monkeypatch.setattr(lock_wait, "LOCK_RETRY_INTERVAL_SECONDS", 0.05, raising=False)

    task = asyncio.create_task(debounce_manager.process_buffered_events(1, 1, "t"))
    await asyncio.sleep(0.15)

    assert buffer.flush_calls == 0
    assert processed == []

    await redis.delete(LOCK_KEY)
    await asyncio.wait_for(task, timeout=5)

    assert buffer.flush_calls == 1
    assert processed == ["hola"]


@pytest.mark.asyncio
async def test_espera_cerrojo_hasta_expirar_y_procesa(
    entorno: tuple[FakeRedis, FakeBuffer, list],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Si el dueño muere, la espera no se descarta: adquiere al expirar el TTL."""
    redis, buffer, processed = entorno
    monkeypatch.setattr(processing_lock, "PROCESSING_LOCK_TTL_SECONDS", 1)
    monkeypatch.setattr(lock_wait, "LOCK_RETRY_INTERVAL_SECONDS", 0.05, raising=False)
    redis.values[LOCK_KEY] = "dueno-caido"
    redis.expiries[LOCK_KEY] = time.monotonic() + 1

    task = asyncio.create_task(debounce_manager.process_buffered_events(1, 1, "t"))
    await asyncio.sleep(0.4)

    assert buffer.flush_calls == 0
    assert processed == []

    await asyncio.wait_for(task, timeout=4)

    assert buffer.flush_calls == 1
    assert processed == ["hola"]


@pytest.mark.asyncio
async def test_timeout_reprograma_y_procesa_sin_nuevo_mensaje(
    entorno: tuple[FakeRedis, FakeBuffer, list],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Al vencer la espera no se consume: se reintenta y procesa solo."""
    redis, buffer, processed = entorno
    monkeypatch.setattr(lock_wait, "LOCK_WAIT_TIMEOUT_SECONDS", 0.2)
    monkeypatch.setattr(lock_wait, "LOCK_RETRY_DELAY_SECONDS", 0.05)
    monkeypatch.setattr(lock_wait, "LOCK_RETRY_INTERVAL_SECONDS", 0.05, raising=False)
    redis.values[LOCK_KEY] = "dueno-lento"

    task = asyncio.create_task(debounce_manager.process_buffered_events(1, 1, "t"))
    await asyncio.wait_for(task, timeout=2)

    # Vencida la espera: el buffer sigue intacto y hay un reintento programado.
    assert buffer.flush_calls == 0
    assert processed == []
    assert buffer.ttl_refreshes > 0
    assert lock_wait._pending_lock_retries

    # Se libera el cerrojo; el reintento debe procesar sin otro mensaje.
    await redis.delete(LOCK_KEY)
    for _ in range(60):
        if processed:
            break
        await asyncio.sleep(0.05)

    assert buffer.flush_calls == 1
    assert processed == ["hola"]
    assert LOCK_KEY not in redis.values


@pytest.mark.asyncio
async def test_cancel_pending_lock_retries_conserva_buffer(
    entorno: tuple[FakeRedis, FakeBuffer, list],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """El apagado cancela los reintentos sin consumir ni borrar el buffer."""
    redis, buffer, processed = entorno
    monkeypatch.setattr(lock_wait, "LOCK_WAIT_TIMEOUT_SECONDS", 0.1)
    monkeypatch.setattr(lock_wait, "LOCK_RETRY_DELAY_SECONDS", 5)
    monkeypatch.setattr(lock_wait, "LOCK_RETRY_INTERVAL_SECONDS", 0.05, raising=False)
    redis.values[LOCK_KEY] = "dueno-activo"

    await debounce_manager.process_buffered_events(1, 1, "t")
    assert lock_wait._pending_lock_retries

    await lock_wait.cancel_pending_lock_retries()

    assert not lock_wait._pending_lock_retries
    assert buffer.flush_calls == 0
    assert processed == []


@pytest.mark.asyncio
async def test_cancelacion_durante_espera_conserva_buffer(
    entorno: tuple[FakeRedis, FakeBuffer, list],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Al apagar, CancelledError no consume ni borra el cerrojo ajeno."""
    redis, buffer, processed = entorno
    monkeypatch.setattr(lock_wait, "LOCK_WAIT_TIMEOUT_SECONDS", 5)
    monkeypatch.setattr(lock_wait, "LOCK_RETRY_INTERVAL_SECONDS", 0.05, raising=False)
    redis.values[LOCK_KEY] = "dueno-activo"

    task = asyncio.create_task(debounce_manager.process_buffered_events(1, 1, "t"))
    await asyncio.sleep(0.1)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    assert buffer.flush_calls == 0
    assert processed == []
    assert redis.values[LOCK_KEY] == "dueno-activo"

    # Los mensajes siguen disponibles para el siguiente intento.
    await redis.delete(LOCK_KEY)
    await debounce_manager.process_buffered_events(1, 1, "t2")
    assert buffer.flush_calls == 1
    assert processed == ["hola"]


@pytest.mark.asyncio
async def test_cerrojo_expirado_permite_reintento_y_no_borra_al_nuevo_dueno(
    entorno: tuple[FakeRedis, FakeBuffer, list],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Si el dueño muere, el TTL libera; el release viejo no toca al nuevo."""
    redis, _buffer, _ = entorno
    monkeypatch.setattr(processing_lock, "PROCESSING_LOCK_TTL_SECONDS", 1)

    viejo = await processing_lock.acquire_processing_lock(1)
    assert viejo
    await asyncio.sleep(1.1)

    nuevo = await processing_lock.acquire_processing_lock(1)
    assert nuevo and nuevo != viejo

    await processing_lock.release_processing_lock(1, viejo)
    assert redis.values[LOCK_KEY] == nuevo


@pytest.mark.asyncio
async def test_renovacion_solo_del_propietario(
    entorno: tuple[FakeRedis, FakeBuffer, list],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis, _buffer, _ = entorno
    monkeypatch.setattr(processing_lock, "PROCESSING_LOCK_TTL_SECONDS", 1)

    token = await processing_lock.acquire_processing_lock(1)
    assert token

    assert await processing_lock.renew_processing_lock(1, "otro-token") is False
    assert await processing_lock.renew_processing_lock(1, token) is True
    assert redis.values[LOCK_KEY] == token


@pytest.mark.asyncio
async def test_renovacion_falla_si_redis_no_esta(
    entorno: tuple[FakeRedis, FakeBuffer, list],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _redis, _buffer, _ = entorno
    token = await processing_lock.acquire_processing_lock(1)
    assert token

    monkeypatch.setattr(dependencies, "redis_connection", None)

    assert await processing_lock.renew_processing_lock(1, token) is False


@pytest.mark.asyncio
async def test_latido_registra_perdida_de_propiedad_y_no_readquiere(
    entorno: tuple[FakeRedis, FakeBuffer, list],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    redis, _buffer, _ = entorno
    monkeypatch.setattr(processing_lock, "LOCK_RENEW_INTERVAL_SECONDS", 0.01)
    token = await processing_lock.acquire_processing_lock(1)
    assert token
    redis.values[LOCK_KEY] = "otro-dueno"

    with caplog.at_level(logging.ERROR):
        await asyncio.wait_for(
            processing_lock.keep_processing_lock_alive(1, token), timeout=1
        )

    assert redis.values[LOCK_KEY] == "otro-dueno"
    assert len(redis.set_calls) == 1  # no se volvió a adquirir
    assert "perdido durante el procesamiento" in caplog.text


@pytest.mark.asyncio
async def test_latido_registra_fallo_de_redis_sin_readquirir(
    entorno: tuple[FakeRedis, FakeBuffer, list],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    redis, _buffer, _ = entorno
    monkeypatch.setattr(processing_lock, "LOCK_RENEW_INTERVAL_SECONDS", 0.01)
    token = await processing_lock.acquire_processing_lock(1)
    assert token

    class RedisQueFalla:
        async def eval(self, *_args: Any, **_kwargs: Any) -> int:
            raise ConnectionError("redis caído")

    monkeypatch.setattr(dependencies, "redis_connection", RedisQueFalla())

    with caplog.at_level(logging.WARNING):
        await asyncio.wait_for(
            processing_lock.keep_processing_lock_alive(1, token), timeout=1
        )

    assert redis.values[LOCK_KEY] == token
    assert len(redis.set_calls) == 1  # no se volvió a adquirir
    assert "No se pudo renovar el cerrojo" in caplog.text


@pytest.mark.asyncio
async def test_sin_redis_para_cerrojo_procesa_sin_cerrojo(
    entorno: tuple[FakeRedis, FakeBuffer, list],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _redis, buffer, processed = entorno
    monkeypatch.setattr(dependencies, "redis_connection", None)

    await debounce_manager.process_buffered_events(1, 1, "t")

    assert buffer.flush_calls == 1
    assert processed == ["hola"]


@pytest.mark.asyncio
async def test_recover_pending_buffers_procesa_al_arrancar_sin_mensaje_nuevo(
    entorno: tuple[FakeRedis, FakeBuffer, list],
) -> None:
    """Una ráfaga que quedó en el buffer se procesa al arrancar.

    No se llama a ``process_buffered_events`` desde un mensaje nuevo: lo hace
    la recuperación de arranque, que descubre el chat en el buffer.
    """
    _redis, buffer, processed = entorno
    assert buffer.batches

    scheduled = await startup_recovery.recover_pending_buffers()
    assert scheduled == 1

    for _ in range(100):
        if processed:
            break
        await asyncio.sleep(0.01)

    assert buffer.flush_calls == 1
    assert processed == ["hola"]


@pytest.mark.asyncio
async def test_lote_consumido_antes_de_apagar_no_se_recupera(
    entorno: tuple[FakeRedis, FakeBuffer, list],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Limitación concreta: si ``flush_all`` ya consumió el lote, no hay replay.

    Se simula el apagado cancelando la tarea después de que tomó los fragmentos
    y antes de completar el procesamiento. La recuperación de arranque no
    encuentra nada porque el buffer y su secuencia ya fueron borrados.
    """
    _redis, buffer, processed = entorno
    started = asyncio.Event()
    release = asyncio.Event()

    async def fake_process(_event: Any) -> None:
        started.set()
        await release.wait()
        processed.append("no-debe-llegar")

    monkeypatch.setattr(debounce_manager, "process_event_task", fake_process)

    task = asyncio.create_task(debounce_manager.process_buffered_events(1, 1, "t"))
    await asyncio.wait_for(started.wait(), timeout=1)
    assert buffer.flush_calls == 1

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    # El lote ya fue consumido; no hay clave que la recuperación pueda ver.
    assert buffer.batches == []
    assert processed == []
    scheduled = await startup_recovery.recover_pending_buffers()
    assert scheduled == 0
    assert processed == []


@pytest.mark.asyncio
async def test_ingestion_buffer_lista_secuencia_y_ttl_de_recuperacion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """El buffer real descubre chats, repara la secuencia y extiende el TTL."""
    redis = FakeRedis()
    monkeypatch.setattr(dependencies, "redis_connection", redis)
    buffer = IngestionBuffer()

    assert await buffer.push_event("1", _fragment("hola")) == 1
    redis.values["clave:ajena"] = "no-es-buffer"

    assert await buffer.list_pending_chats() == [1]

    # El contador puede expirar antes que la lista; ensure_sequence lo repara.
    await redis.delete("ingest:seq:1")
    assert await buffer.ensure_sequence("1") == 1
    assert await buffer.get_current_sequence("1") == 1
    assert redis.expiries["ingest:seq:1"] > time.monotonic()

    assert await buffer.extend_pending_ttl() == 1
    for key in ("ingest:buffer:1", "ingest:seq:1"):
        remaining = redis.expiries[key] - time.monotonic()
        assert 3590 < remaining <= 3600
