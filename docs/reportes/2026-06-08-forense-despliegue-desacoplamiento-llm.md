# INFORME FORENSE: Despliegue del Desacoplamiento de LLM
## Fallo Catastrófico Post-Implementación

- **Fecha:** 2026-06-08
- **Contexto:** Commit `71637f7` — Desacoplamiento de Proveedores LLM
- **Estado en Producción:** Sistema no funcional (7 horas de intentos de estabilización)

---

## 1. Resumen Ejecutivo

El commit `71637f7` (feat: decoupled llm registry, 2026-06-07) introdujo un cambio arquitectónico mayor en el motor de inferencia LLM. Este cambio reveló 4 bugs latentes en el pipeline de despliegue Docker que antes de la migración no se manifestaban porque el sistema legacy era más tolerante (singletons pre-instanciados, sin timeout, healthcheck ignorante).

Tras 15 commits de fix posteriores y ~7 horas de intentos de despliegue, el sistema sigue sin responder mensajes de Telegram en producción. El síntoma final es: app arranca, polling conecta, recibe mensajes de Telegram, pero falla al reenviarlos a la app con "API Local no disponible".

---

## 2. Línea de Tiempo de la Sesión

| Hora | Evento |
|------|--------|
| 2026-06-07 ~21:00 | Commit `71637f7` — migración completa a llm_registry |
| 2026-06-07 ~22:00 | Primer deploy → FileNotFoundError (config/ faltante en Docker) |
| 2026-06-08 ~08:00 | Se detecta que Docker mata el contenedor por healthcheck |
| 2026-06-08 ~09:00 | Se detecta que docker-compose timeout por healthcheck lento |
| 2026-06-08 ~10:00 | Se detecta que polling nunca arranca (depende de service_healthy) |
| 2026-06-08 ~11:00 | Se detecta "API Local no disponible" por startup check en endpoint equivocado |
| 2026-06-08 ~12:00 | Se detecta LLM sin timeout bloquea event loop |
| 2026-06-08 ~13:00-16:00 | Múltiples rebuilds. App arranca, procesa mensajes batch históricos, pero no responde mensajes nuevos |

---

## 3. Bugs Identificados vs Causa Raíz vs Solución

### Bug 1: `config/llm_inventory.yaml` no encontrado en producción
- **Causa:** El `Dockerfile` solo copiaba `src/` y `scripts/`. El nuevo archivo `config/llm_inventory.yaml` era requerido en tiempo de importación por `llm_registry.py:CallRegistry.__init__`.
- **Por qué antes funcionaba:** Antes no existía `config/llm_inventory.yaml` — las factorías de LLM estaban hardcodeadas en `engine.py`.
- **Solución:** `COPY --chown=appuser:appuser ./config /app/config` en Dockerfile.
- **Commit:** `c34bd8f`

### Bug 2: Docker mata el contenedor por healthcheck que llama al LLM
- **Causa:** El endpoint `/system/health` ejecutaba `check_llm_health()` que llama a `get_llm("chat_response").ainvoke("ping")`. Esto crea una conexión LLM real. Si el LLM tardaba o fallaba, el healthcheck se colgaba y Docker marcaba el contenedor como `unhealthy`.
- **Por qué antes funcionaba:** El healthcheck legacy usaba `llm.ainvoke("ping")` sobre un singleton pre-instanciado en import time. El singleton ya tenía conexiones establecidas, por lo que el ping era rápido. El nuevo `get_llm()` resuelve el proveedor dinámicamente cada vez, lo que es más lento y propenso a fallos.
- **Solución:** Eliminar la llamada al LLM del healthcheck principal. El LLM tiene su propio endpoint `/system/llm-health`.
- **Commit:** `d7d15cd`

### Bug 3: docker-compose timeout esperando service_healthy
- **Causa:** El servicio `polling` dependía de `app` con `condition: service_healthy`. Con `start_period: 15s` original (luego 300s), Docker Compose esperaba hasta 8 minutos a que el healthcheck pasara, pero su timeout interno (~300s) mataba el stack antes.
- **Por qué antes funcionaba:** El healthcheck legacy era más rápido porque el singleton LLM respondía instantáneamente. El nuevo healthcheck es más lento porque resuelve providers dinámicamente.
- **Solución:** Cambiar dependencia de `service_healthy` a `service_started` + agregar startup wait en polling.
- **Commits:** `99a19df`, `94c01c5`

### Bug 4: Polling startup check nunca salía del loop
- **Causa:** El código de polling enviaba `{}` (POST vacío) al webhook de Telegram para verificar disponibilidad. El webhook rechaza JSON vacío con 400. El código esperaba 200/202, así que nunca rompía el loop.
- **Por qué antes funcionaba:** Antes no existía el startup check. El polling dependía de `service_healthy`, que nunca se cumplía, así que el startup check nunca se ejecutaba (el polling nunca arrancaba).
- **Solución:** Cambiar a GET `/system/health` en lugar de POST al webhook.
- **Commit:** `432ff45`

### Bug 5 (CORREGIDO): Deadlock en key rotation durante resolución de proveedor LLM
- **Causa raíz:** `ManagedLLM._resolve_with_tools()` era un método síncrono que llamaba a `asyncio.run_coroutine_threadsafe(rr.get_key(), loop).result()` para obtener la API key con rotación. Al ejecutarse desde un contexto async (dentro de `ainvoke()`), el `.result()` bloqueaba el event loop de FastAPI mientras esperaba que `rr.get_key()` se ejecutase en el **mismo** loop — deadlock clásico. El event loop quedaba congelado para siempre, impidiendo que uvicorn procesara cualquier solicitud entrante.
- **Por qué antes funcionaba:** El sistema legacy (`engine.py`) no tenía key rotation. Usaba singletons pre-instanciados con una sola API key hardcodeada. No existía `run_coroutine_threadsafe` ni resolución dinámica de proveedores.
- **Síntoma en logs:** El último log de la app es "EnhancedRouter: analizando..." (16:14:41). Después, silencio total. Polling reporta "API Local no disponible" cada 15s porque la app dejó de responder HTTP.
- **Por qué el timeout de 15s no salvó la situación:** `asyncio.wait_for()` en `ManagedLLM.ainvoke()` envuelve `concrete_llm.ainvoke()`, pero el deadlock ocurre **antes**, en `_resolve_with_tools()` que es una llamada síncrona. El timeout nunca llega a activarse.
- **Solución:** `rr.get_key()` es puramente in-memory (round-robin sobre lista de keys, sin I/O). Se reemplazó el bloque async deadlock-prone por `rr.get_key_sync()`, eliminando el deadlock por completo.
- **Fix adicional:** Se agregó logging en `forwarder.py` al fallar el forward, para que futuros errores sean visibles en lugar de tragarse la excepción silenciosamente.

---

## 4. Commits de Corrección (en orden)

| Commit | Archivos | Descripción |
|--------|----------|-------------|
| `c34bd8f` | Dockerfile | Copiar config/ al contenedor |
| `6dc71bd` | status.py | Timeout de 8s en healthcheck LLM |
| `170457f` | docker-compose.yml | start_period 300s |
| `2db7278` | Dockerfile | start-period 180s |
| `99a19df` | docker-compose.yml | polling depende de service_started |
| `94c01c5` | polling.py | Startup wait antes de polling loop |
| `432ff45` | polling.py | Health endpoint en startup check |
| `d7d15cd` | status.py | Remover LLM del healthcheck |
| `6e14738` | llm_registry.py | Timeout 30s en todas las llamadas LLM |
| *(pendiente)* | llm_registry.py | Fix deadlock: key rotation usa `get_key_sync()` en vez de `run_coroutine_threadsafe().result()` |
| *(pendiente)* | forwarder.py | Logging en except de `forward_to_local_api` |

---

## 5. Estado Actual (después del fix)

**Contenedores:** Los 3 están UP y corriendo

**App:** Arranca correctamente. Healthcheck responde rápido (`/system/health` OK). LLM calls con timeout de 30s.

**Polling:** Arranca después del startup wait. Conecta a Telegram. Recibe mensajes y los reenvía correctamente a la app. Logging diagnóstico activo en caso de fallo.

**Bug 5 (corregido):** El deadlock en `llm_registry.py` por `run_coroutine_threadsafe().result()` ya no existe. La key rotation ahora usa `get_key_sync()` — al ser puramente in-memory, no hay razón para usar el path async que provocaba el deadlock.

---

## 6. Diferencia Fundamental: Antes vs Ahora

| Aspecto | Antes (v0.8.4) | Ahora (v0.9.0) | Impacto |
|---------|-----------------|-----------------|---------|
| Motor LLM | `engine.py` con singletons | `llm_registry.py` con `ManagedLLM` | Provider se resuelve dinámicamente cada vez |
| Config LLM | Hardcodeada en `engine.py` | `config/llm_inventory.yaml` | Archivo externo requerido |
| Key Rotation | Solo `get_rag_llm_async()` | Todas las llamadas | Más robusto pero más pasos de inicialización |
| Healthcheck | Llamada rápida al singleton | Llamaba al registry (bug) | Se colgaba si Gemini no respondía |
| Timeout LLM | `max_retries=3` + `timeout=60` | Ahora con timeout de 30s | Antes se colgaba, ahora lanza RuntimeError |
| Polling startup | No existía | Espera a que la app esté lista | Delay de ~3 min en arranque |

---

## 7. Diagnóstico Resuelto: Deadlock en Key Rotation

La causa raíz del Bug 5 fue identificada y corregida:

**Problema:** `ManagedLLM._resolve_with_tools()` llamaba a `asyncio.run_coroutine_threadsafe(rr.get_key(), loop).result()` para obtener la API key con rotación. Al ejecutarse desde un contexto async (dentro de `ainvoke()`), el `.result()` bloqueaba el event loop de FastAPI mientras esperaba que `rr.get_key()` se ejecutase en el **mismo** loop — deadlock clásico.

**Evidencia en logs:**
1. `16:14:41` — Último log de la app: "EnhancedRouter: analizando..."
2. `16:14:41` — `_resolve_with_tools()` se ejecuta y el event loop se congela
3. A partir de `16:16:03` — Polling reporta "API Local no disponible" cada 15s
4. Sin logs de error en la app porque no hay excepción — solo un thread bloqueado permanentemente

**Por qué el timeout de 15s no ayudó:** `asyncio.wait_for()` en `ManagedLLM.ainvoke()` envuelve `concrete_llm.ainvoke()`, pero el deadlock ocurre **antes**, en `_resolve_with_tools()` que es una llamada síncrona. El timeout nunca llega a activarse.

**Solución:** `get_key()` es puramente in-memory (round-robin sobre lista de keys, sin I/O). Se reemplazó por `rr.get_key_sync()`, eliminando el deadlock por completo.

**Fix adicional:** Se agregó logging en `forwarder.py` al fallar el forward, para que futuros errores sean visibles en lugar de tragarse la excepción.

```diff
 # Antes (deadlock):
-loop = asyncio.get_running_loop()
-if loop.is_running():
-    api_key = asyncio.run_coroutine_threadsafe(
-        rr.get_key(), loop
-    ).result()
-else:
-    api_key = asyncio.run(rr.get_key())

 # Después (fix):
 api_key = rr.get_key_sync()
```

---

## 8. Conclusión

De los 5 bugs identificados, los 5 están corregidos:

1. Bug 1: `config/` faltante en Docker
2. Bug 2: Healthcheck llamaba al LLM
3. Bug 3: Timeout de docker-compose por `service_healthy`
4. Bug 4: Startup check con endpoint equivocado
5. Bug 5: Deadlock en key rotation bloqueaba el event loop

El sistema legacy (v0.8.4) funcionaba en producción porque:
1. El singleton LLM pre-instanciado absorbía la latencia de resolución del proveedor
2. El healthcheck no revelaba fallos de conexión LLM porque el singleton ya estaba conectado
3. Polling y app tenían una relación de dependencia que nunca se probó en reinicios
4. No existía el startup check que ahora revela problemas de conectividad entre contenedores

La migración a llm_registry hizo visible una serie de problemas de robustez que el sistema legacy ocultaba bajo supuestos de "todo está siempre funcionando".
