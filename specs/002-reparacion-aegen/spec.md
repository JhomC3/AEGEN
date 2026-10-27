# Spec 002 — Reparación del recorrido de respuesta de AEGEN

Nivel: **localizado** (varios módulos del recorrido, sin cambios de interfaces
en `src/core/interfaces/`, sin cambios de schemas ni del contrato del bus).
Plan y tareas viven en esta misma spec, conforme al proceso común
(`../sdd-kit/SDD_BOOTSTRAP.md` §1.2 y §5–§7).

Fecha: 2026-10-21. Autorización de alcance: el encargo vigente pide reparar y
estabilizar recepción, routing/ejecución y respuesta **antes** de integrar
SENDA, con errores honestos y sin tocar el dominio SENDA. Esta spec no autoriza
despliegue, commits, push ni cambios de infraestructura.

## Contexto y objetivo

El recorrido Telegram → webhook → debounce → orquestador → especialista →
respuesta contiene puntos donde un fallo se convierte en éxito aparente o en
silencio: el mensaje de error puede perderse, dos ráfagas del mismo chat pueden
procesarse a la vez, una herramienta que falla devuelve texto y el estado sigue
marcado como exitoso, el chat traga la excepción del proveedor LLM, la búsqueda
semántica puede bloquear o tumbar la respuesta cuando el proveedor de embeddings
falla, y `/system/health` declara salud LLM sin haberla comprobado.

Objetivo: que un mensaje reciba siempre una respuesta o un error explícito y
trazable; que los fallos de dependencias opcionales (Redis, embeddings) degraden
sin bloquear; y que las pruebas reproduzcan cada defecto antes de repararlo.

## Usuarios / actores

- Dueño/operador de AEGEN, que diagnostica por logs y health checks.
- Usuarios de Telegram, que necesitan saber si su solicitud se completó o no.
- Agentes de mantenimiento, que deben poder confiar en el estado reportado.

## Historias de usuario

- H1: Como usuario de Telegram quiero recibir la respuesta del especialista o un
  error claro, nunca un mensaje que oculte el fallo.
- H2: Como operador quiero que una ráfaga doble no ejecute dos veces la misma
  respuesta ni consuma dos veces el buffer.
- H3: Como operador quiero que un fallo de LLM o de una herramienta quede
  marcado como error en el estado y en los logs, no como respuesta válida.
- H4: Como operador quiero que la caída de embeddings o Redis degrade la
  memoria sin impedir que el chat responda.
- H5: Como operador quiero que `/system/health` no afirme que el LLM está bien
  si nunca se comprobó.
- H6: Como operador quiero que los mensajes que quedaron en el buffer al apagar
  se procesen al arrancar, sin depender de que el usuario envíe otro mensaje, y
  que el lote ya consumido no se presente como recuperado si no lo está.

## Requisitos funcionales (criterios de aceptación en EARS)

- **RF-1** CUANDO el estado final contiene `error_message` no vacío, EL SISTEMA
  envía a Telegram un mensaje de error explícito y seguro para el usuario, y
  registra en logs el detalle técnico.
- **RF-2** SI el estado final no contiene `response` utilizable pero sí
  `error_message`, ENTONCES EL SISTEMA envía el error de RF-1 y **no** el
  mensaje «respuesta vacía».
- **RF-3** CUANDO el estado final contiene `response` no vacío y no hay
  `error_message`, EL SISTEMA envía esa respuesta tal cual.
- **RF-4** SI no hay `response` ni `error_message`, ENTONCES EL SISTEMA envía el
  mensaje de fallback de respuesta vacía existente.
- **RF-5** CUANDO dos tareas de debounce del mismo chat intentan procesar a la
  vez, EL SISTEMA adquiere el cerrojo de forma atómica (`SET NX EX`); la tarea
  que no lo obtiene espera de forma acotada (30 s) y, si vence, reprograma la
  ráfaga con el mismo `task_seq` sin consumir el buffer. Tras 2 s vuelve a
  intentar el flujo completo; si vuelve a vencer, repite. No depende de un
  mensaje nuevo del usuario y no procesa en paralelo en condiciones normales.
  Al obtener el cerrojo, consume el buffer si sigue siendo la tarea vigente.
  Ninguna ráfaga se descarta por encontrar el chat ocupado.
- **RF-6** CUANDO el cerrojo se libera, EL SISTEMA solo lo borra si el token
  corresponde a la tarea que lo adquirió.
- **RF-7** SI el cliente Redis usado por el cerrojo no está disponible pero el
  buffer de ingesta sí puede operar (por ejemplo, un backend alternativo o un
  doble de prueba), ENTONCES EL SISTEMA procesa sin cerrojo y no falla por esa
  causa. Sin Redis real tampoco hay buffer persistente; ese límite se registra
  en «Riesgos residuales».
- **RF-16** MIENTRAS una tarea procesa, EL SISTEMA renueva el cerrojo cada
  `TTL/3`; si la tarea muere, el TTL expira y otra tarea puede adquirirlo. Si
  Redis falla durante la renovación o el token deja de coincidir, EL SISTEMA
  registra el fallo, deja de renovar y **no re-adquiere** el cerrojo; el
  procesamiento en curso continúa. En condiciones normales (Redis disponible y
  latido al día), el mismo chat no debe tener dos procesamientos simultáneos;
  el bloqueo del event loop es un riesgo residual no resuelto (ver «Riesgos
  residuales»).
- **RF-17** CUANDO la aplicación se apaga, EL SISTEMA cancela los reintentos de
  cerrojo pendientes y propaga `CancelledError`; mientras el reintento siga
  esperando, no consume ni borra el buffer de mensajes. Si la cancelación llega
  después de consumirlo, aplica el riesgo residual documentado.
- **RF-18** MIENTRAS una ráfaga espera el cerrojo, EL SISTEMA renueva el TTL del
  buffer y del contador de secuencia para que no expire durante la espera o el
  reintento.
- **RF-19** CUANDO la aplicación arranca y existen listas `ingest:buffer:*`
  vivas, EL SISTEMA descubre los chats, repara el contador de secuencia si
  expiró y programa `process_buffered_events` en segundo plano sin esperar un
  mensaje nuevo. La recuperación no bloquea el arranque de la API.
- **RF-20** CUANDO la aplicación se apaga de forma ordenada, EL SISTEMA extiende
  el TTL de los buffers pendientes a 3600 s (ventana de reinicio) y cancela las
  recuperaciones y reintentos en curso. Si aún no consumieron el buffer, este se
  conserva; si ya lo consumieron, aplica RF-21. Un `SIGKILL` no ejecuta esta
  extensión y deja el TTL normal de 60 s; si el reinicio supera la ventana,
  Redis descarta los mensajes. Es una limitación declarada, no una garantía de
  persistencia.
- **RF-21** SI `flush_all` ya consumió el lote antes de que el apagado cancele
  el procesamiento, ENTONCES EL SISTEMA no lo recupera: no existe cola durable
  ni replay del lote en vuelo. La recuperación de arranque encuentra el buffer
  vacío y no procesa nada. La limitación es concreta y medible: se demuestra con
  `test_lote_consumido_antes_de_apagar_no_se_recupera`; no se declara resuelta.
- **RF-8** CUANDO la invocación de la herramienta de un skill lanza una
  excepción, EL SISTEMA registra el fallo, marca `error_message` en el estado y
  devuelve un texto de fallo explícito; el evento no cuenta como éxito.
- **RF-9** CUANDO el proveedor LLM del chat lanza una excepción, EL SISTEMA no la
  convierte en una respuesta de disculpa silenciosa: la propaga para que RF-8 la
  marque y la registra con traza.
- **RF-10** SI el proveedor de embeddings falla, ENTONCES la búsqueda híbrida
  continúa con resultados de palabra clave (FTS5), registra una advertencia y no
  impide la respuesta del chat.
- **RF-11** CUANDO se generan embeddings, EL SISTEMA ejecuta la llamada
  sincrónica del SDK fuera del event loop.
- **RF-12** SI `GOOGLE_API_KEY` no está configurada, ENTONCES la construcción de
  `EmbeddingService` no tumba el arranque; el fallo se produce solo al intentar
  usar embeddings y se degrada según RF-10.
- **RF-13** CUANDO se consulta `/system/health`, EL SISTEMA reporta
  `llm_connection` como `pending` si nunca se ejecutó `/system/llm-health`, y
  usa el último resultado real cacheado mientras esté fresco (5 min); fuera de
  ese TTL vuelve a `pending` en vez de afirmar salud sin evidencia reciente.
- **RF-14** CUANDO se ejecuta `/system/llm-health`, EL SISTEMA actualiza el
  caché de salud con el resultado real (`ok` o `error`).
- **RF-15** EL SISTEMA conserva intactos los cambios locales de integración
  SENDA (routing, config, skill `bienestar`, polling) y no escribe en el dominio
  SENDA.

## Requisitos no funcionales

- Sin dependencias nuevas.
- Sin cambios en `src/core/interfaces/`, `src/core/schemas/` ni en
  `CanonicalEventV1`.
- Los mensajes al usuario no incluyen trazas, rutas internas, tokens ni
  respuestas crudas de proveedores; el detalle queda en logs.
- Compatibilidad con Redis ausente y con proveedor de embeddings caído.
- Idioma de mensajes y documentación: español.

## Casos límite

- `response` es `None`, cadena vacía o solo espacios.
- `payload` ausente o `None` en el estado final.
- `error_message` y `response` presentes a la vez (RF-1 prevalece).
- Fallo al enviar a Telegram: se registra y no se relanza.
- Dos ráfagas concurrentes con y sin Redis.
- Ráfaga que llega mientras otra procesa: espera acotada, se reprograma y se
  atiende después sin un mensaje nuevo.
- Cerrojo cuyo TTL expira antes de liberar: la liberación no debe borrar el
  cerrojo de otra tarea y la tarea en espera debe poder adquirirlo.
- Procesamiento más largo que el TTL: el latido debe renovar y evitar que otra
  tarea entre en paralelo mientras el event loop siga atendiendo el latido.
- Fallo de Redis durante la renovación o pérdida del token: se registra y no se
  re-adquiere; el riesgo de solapamiento queda documentado, no resuelto.
- Apagado durante la espera: `CancelledError` no consume el buffer, no borra el
  cerrojo ajeno y cancela los reintentos programados.
- Espera más larga que el TTL del buffer: el TTL se renueva para no perder los
  mensajes pendientes.
- Reinicio ordenado con fragmentos en el buffer: se descubren al arrancar y se
  procesan sin mensaje nuevo.
- Reinicio tras más de 3600 s desde el apagado, o tras `SIGKILL` y más de 60 s:
  Redis ya borró las claves; no hay recuperación posible.
- Contador de secuencia ausente con lista de fragmentos viva: se repara la
  secuencia al arrancar.
- Apagado después de `flush_all`: el lote no se recupera (RF-21).
- Proveedor de embeddings lento o caído; caché de embeddings con hits parciales.
- `/system/health` antes y después de `/system/llm-health`.

## Fuera de alcance

- Sustituir la `GOOGLE_API_KEY` inválida o contratar otro proveedor. Es un
  bloqueo externo: sin clave válida no hay embeddings nuevos; solo se garantiza
  la degradación.
- Cambiar el modelo, el routing, el pipeline o la arquitectura.
- Desplegar en GCP, crear recursos, tocar Docker, Redis o el proceso SENDA.
- Herramientas que convierten una excepción en texto de error en vez de
  relanzarla (`src/personality/skills/transcription/tools.py`,
  `src/tools/document_processing.py`, `src/tools/image_processing.py`): no
  están en los módulos reparados y no se declaran reparadas. Si el usuario ve
  ese texto, puede parecer una respuesta válida; queda como hallazgo abierto.
- Reparar los fallos preexistentes de tests, ajenos a esta reparación y
  registrados sin declararlos reparados:
  - `tests/unit/personality/test_bienestar_skill.py::test_undo_aborta_si_lectura_de_huella_falla`:
    el test usa «hoy» (2026-10-21) pero fija `fecha_iso` en `2026-10-04`, por lo
    que la huella de `_ULTIMAS` no coincide y no se ejecuta la comprobación que
    el test pretende. Es trabajo local sin seguimiento del usuario; se registra,
    no se modifica.
  - `tests/unit/orchestrator/test_context_retriever.py::test_context_retriever_analytical_intent`:
    el test no mockea `_check_edges_exist`; con `AsyncMock` no hay DB real y
    `graph_fragments` queda vacío, por lo que la aserción falla. Defecto de
    test, no de producto.
  - `tests/unit/memory/test_atomic_knowledge.py::test_save_knowledge_atomic`:
    `KeyError: 'user_name'` al cargar el conocimiento; el fixture no reproduce
    la forma que el test espera. Defecto de test.
  - `tests/unit/memory/test_hierarchical_ingestion.py::test_hierarchical_ingestion_flow`:
    el test construye `IngestionPipeline` antes de parchear `EmbeddingService`,
    así que la instancia real ya existe y la llamada real falla con
    `API_KEY_INVALID`. Defecto de test (orden del mock), no de la reparación.
- Reparar los 83 hallazgos preexistentes de `ruff check .` ni el timeout de la
  suite completa; se validará por archivos y subsistemas tocados.

## Plan de implementación

1. **Respuesta y errores** (`src/api/services/event_processor.py`): precedencia
   explícita error → respuesta → fallback; acceso seguro a `payload`; mensaje
   seguro para el usuario. En `master_orchestrator.py`, no volcar la excepción
   cruda en `error_message`.
2. **Cerrojo** (`src/api/services/processing_lock.py`,
   `src/api/services/lock_wait.py`, `src/api/services/debounce_manager.py`):
   separar adquisición/renovación/liberación y espera/reintentos del flujo de
   ráfaga, conservando `process_buffered_events` y
   `cancel_pending_lock_retries` como nombres públicos. Sustituir `get` +
   `setex` por `set(nx=True, ex=...)` con token; esperar de forma acotada y
   reprogramar sin consumir el buffer; renovar con comparación de token mientras
   se procesa; liberar con borrado atómico solo del propietario; renovar el TTL
   del buffer durante la espera; cancelar reintentos en el apagado.
3. **Recuperación al arrancar** (`src/api/services/startup_recovery.py`,
   `src/core/ingestion_buffer.py`, `src/main.py`): descubrir
   `ingest:buffer:*`, reparar la secuencia ausente, programar el procesamiento
   sin mensaje nuevo y extender el TTL a 3600 s en apagado ordenado. Documentar
   que un lote consumido por `flush_all` no tiene replay.
4. **Skills** (`src/agents/specialists/skill_based_specialist.py`): marcar
   `error_message` y devolver fallo explícito al capturar excepciones.
5. **Chat** (`src/personality/skills/chat/tools.py`): registrar y relanzar el
   fallo del LLM.
6. **Embeddings** (`src/memory/embeddings.py`, `src/memory/hybrid_search.py`):
   inicialización no fatal, llamada en hilo y fallback a FTS5.
7. **Salud** (`src/api/routers/status.py`): `pending` sin evidencia y caché
   actualizado por `/system/llm-health`.
8. **Pruebas**: regresiones nuevas por RF, recuperación al arrancar, límite del
   lote consumido y actualización del test de integración de Telegram al
   contrato real (`get_telegram_manager().send_message`).

## Tareas y criterio de «hecho»

- **T1** Spec registrada antes del código. Hecho cuando: este archivo existe y
  los RF cubren los defectos diagnosticados.
- **T2** Reproducir con tests: precedencia de respuesta, cerrojo concurrente,
  error de skill, fallo de chat, fallback de embeddings, salud LLM y
  recuperación de buffers al arrancar. Hecho cuando: cada test falla con el
  código actual o se demuestra que el defecto es de test (integración Telegram)
  y pasa tras el ajuste.
- **T3** Aplicar reparaciones T1–T8 del plan. Hecho cuando: los tests de T2 pasan
  y no hay regresiones en los tests dirigidos existentes.
- **T4** Validar: `ruff check` y `mypy` sobre archivos tocados; `pytest` de los
  módulos afectados; `tests/integration/test_telegram_webhook.py`. Hecho cuando:
  la salida se muestra y los fallos preexistentes quedan identificados.
- **T5** Entregar un **procedimiento único** de verificación, despliegue,
  respaldo y rollback, sin ejecutarlo. Hecho cuando: `despliegue.md` contiene
  inventario del estado real de solo lectura, decisión del entorno de validación,
  respaldo con `BACKUP_PATH` explícito, manifiesto verificado, build abortable,
  validación y rollback por IDs exactos; no se usó ningún respaldo “más
  reciente”. El inventario es estrictamente de lectura: sin `fetch`, `prune`,
  `checkout` ni `pull`, y advierte que las referencias locales pueden estar
  desactualizadas.
- **T6** Incluir la validación real por Telegram en ese mismo procedimiento
  (conversación, ráfaga y herramienta no destructiva), sin iniciar otro bot ni
  otro polling con el mismo token. Hecho cuando: el documento indica quién
  ejecuta, qué mensajes, qué logs se recogen, qué comandos de lectura debe
  pegar el propietario y qué bloqueos impiden ejecutarla hoy.

## Evidencia base (2026-10-21, antes de la reparación)

- `tests/integration/test_telegram_webhook.py::test_telegram_webhook_success_flow`
  falla porque mockea `reply_to_telegram_chat`, pero el código llama a
  `get_telegram_manager().send_message`.
- `tests/unit/personality/test_bienestar_skill.py::test_undo_aborta_si_lectura_de_huella_falla`
  falla por desalineación de fechas en el propio test (ver Fuera de alcance).
- `ruff check .`: 83 hallazgos preexistentes; no se abordan en esta unidad.
- La suite completa no terminó en 15 minutos; se usa validación dirigida.
- `GOOGLE_API_KEY` actual es rechazada por Google (`400 API_KEY_INVALID`); Groq
  responde y el fallback de chat funciona.

## Estado de implementación y evidencia (2026-10-21)

### Adaptación operativa al inventario aportado por el dueño

El 2026-10-21 el dueño autorizó preparar el procedimiento, sin desplegar.
La VM está en `1148766` con cambios de SENDA sin consolidar; no se exige
limpiarla ni se cambia de rama. Se prepara una entrega separada que superpone
solo los 13 archivos de la reparación sobre las imágenes existentes de app y
polling, verificando primero su código contra esa base. Se conservan las
dependencias instaladas, `.env`, `storage`, Redis y Tailscale. El respaldo
conserva las imágenes por ID y permite rollback sin reconstruir ni tocar Git.
Preparación y activación son comandos separados; esta última sigue pendiente
de autorización. El detalle ejecutable único vive en `despliegue.md` y
`operacion/`. No cambia ningún requisito funcional del bot.

Reparaciones aplicadas en el árbol de trabajo, sin commit ni despliegue. La
división del debounce dejó `debounce_manager.py` en 133 líneas, con el cerrojo
en `processing_lock.py` (134), la espera/reintentos en `lock_wait.py` (147) y
la recuperación de arranque en `startup_recovery.py` (98); los nombres públicos
`process_buffered_events` y `cancel_pending_lock_retries` se conservan. La
recuperación descubre `ingest:buffer:*` al arrancar y no espera un mensaje
nuevo; el lote ya consumido por `flush_all` no tiene replay (RF-21).

| RF | Evidencia |
|---|---|
| RF-1, RF-2 | `test_error_sin_respuesta_envia_error_no_fallback`, `test_error_prevalece_sobre_respuesta` |
| RF-3 | `test_respuesta_valida_se_envia_tal_cual` |
| RF-4 | `test_respuesta_vacia_y_sin_error_usa_fallback` |
| RF-1 (payload ausente) | `test_payload_ausente_no_lanza` |
| RF-1 (fallo de envío) | `test_fallo_de_telegram_no_relanza` |
| RF-5 | `test_rafaga_durante_procesamiento_se_atiende_despues`, `test_rafaga_durante_procesamiento_llega_a_telegram`, `test_espera_cerrojo_ajeno_y_procesa_al_liberarse`, `test_espera_cerrojo_hasta_expirar_y_procesa`, `test_timeout_reprograma_y_procesa_sin_nuevo_mensaje` |
| RF-5 (adquisición atómica) | `test_cerrojo_adquirido_es_atomico_y_se_libera` |
| RF-6 | `test_cerrojo_ajeno_no_se_borra`, `test_cerrojo_expirado_permite_reintento_y_no_borra_al_nuevo_dueno` |
| RF-7 | `test_sin_redis_para_cerrojo_procesa_sin_cerrojo` (usa `FakeBuffer`; demuestra el cerrojo, no un Redis real caído) |
| RF-8 | `test_fallo_de_herramienta_marca_error_message` |
| RF-9 | `test_fallo_del_llm_se_propaga` |
| RF-10 | `test_busqueda_hibrida_cae_a_keyword_si_embeddings_falla` |
| RF-11 | `test_embedding_se_ejecuta_fuera_del_event_loop` |
| RF-12 | `test_sin_clave_no_tumba_el_arranque` |
| RF-13 | `test_sin_evidencia_reporta_pending` |
| RF-14 | `test_llm_health_sano_actualiza_cache`, `test_llm_health_caido_actualiza_cache` |
| RF-16 | `test_renovacion_evita_procesamiento_simultaneo_al_expirar_ttl`, `test_renovacion_solo_del_propietario`, `test_renovacion_falla_si_redis_no_esta`, `test_latido_registra_perdida_de_propiedad_y_no_readquiere`, `test_latido_registra_fallo_de_redis_sin_readquirir` |
| RF-17 | `test_cancelacion_durante_espera_conserva_buffer`, `test_cancel_pending_lock_retries_conserva_buffer` |
| RF-18 | `test_timeout_reprograma_y_procesa_sin_nuevo_mensaje` (verifica `ttl_refreshes > 0`) |
| RF-19 | `test_recover_pending_buffers_procesa_al_arrancar_sin_mensaje_nuevo`, `test_ingestion_buffer_lista_secuencia_y_ttl_de_recuperacion` |
| RF-20 | `test_ingestion_buffer_lista_secuencia_y_ttl_de_recuperacion` (extiende buffer y secuencia a 3600 s); apagado ordenado en `main.py` |
| RF-21 | `test_lote_consumido_antes_de_apagar_no_se_recupera` (limitación declarada, sin replay) |
| RF-15 | `git status`/`git diff`: los cambios locales de SENDA (`apps/`, `ops/`, `entrega-senda/`, routing, config, polling, skill `bienestar`) siguen intactos; el diff de esta reparación se limita a los 13 archivos fuente y 7 tests listados abajo |

El cambio de `master_orchestrator` (mensaje genérico al usuario, detalle en
logs) se verificó por lectura: es una constante sin ramas; la evidencia de
comportamiento de RF-1 está en `_send_response`.

Comandos y resultados:

- `uv run python -m pytest` sobre los 6 archivos nuevos y
  `tests/integration/test_telegram_webhook.py`: **34 passed**.
- Repetición en una copia temporal de `HEAD` limpio + **solo** los 13 archivos
  fuente y 7 tests de esta reparación (sin los cambios locales de SENDA):
  **34 passed**, con `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` y
  `GOOGLE_API_KEY` de prueba (placeholders, no secretos reales). Confirma que la
  rama de despliegue no depende de los cambios de SENDA.
- `uv run python -m pytest tests/unit/api`: **30 passed**.
- `uv run python -m pytest tests/unit/api/test_debounce_lock.py`: **19 passed**
  (incluye timeout, cancelación, TTL, recuperación al arrancar y el límite del
  lote ya consumido).
- `uv run python -m pytest tests/unit/orchestrator tests/unit/personality`:
  **67 passed, 2 failed** (`test_context_retriever_analytical_intent` y el test
  de `bienestar` preexistente de la tabla anterior).
- `uv run python -m pytest tests/unit/memory`: **67 passed, 2 failed**
  (`test_atomic_knowledge`, `test_hierarchical_ingestion`; preexistentes).
- `uv run python -m ruff check` sobre los 13 archivos fuente y los 7 tests:
  **All checks passed**.
- `uv run python -m mypy` sobre los 13 archivos fuente y los 7 tests:
  **Success: no issues found**.
- `uv run python scripts/simple_check.py`: termina con `Done`; ya **no** reporta
  `debounce_manager.py` (133 líneas) ni los tres módulos nuevos. Conserva 49
  avisos preexistentes de funciones >50 líneas y 10 archivos >200 líneas que ya
  superaban el límite antes de esta ronda (incluido `chat/tools.py`, tocado solo
  funcionalmente en la ronda anterior). La división quedó completada; no se
  difirió.

Archivos fuente de esta reparación (13): `event_processor.py`,
`debounce_manager.py`, `processing_lock.py`, `lock_wait.py`,
`startup_recovery.py`, `status.py`, `skill_based_specialist.py`,
`master_orchestrator.py`, `chat/tools.py`, `embeddings.py`, `hybrid_search.py`,
`ingestion_buffer.py` y `main.py`. Tests: los 6 archivos nuevos y
`tests/integration/test_telegram_webhook.py` (7 en total; el test de debounce
contiene 19 casos). Documentación: `spec.md`, `despliegue.md` y
`evidencia-preexistentes.md`.

### Prueba de fallos preexistentes (2026-10-21)

Se ejecutaron las pruebas sospechosas contra el código de `HEAD` en un
directorio temporal (`git archive HEAD | tar -x -C "$TMP"`), sin stash, sin
worktree y sin tocar el árbol de trabajo. Resultado: **4 failed**:

- `test_context_retriever_analytical_intent`: `assert 0 == 1`.
- `test_atomic_knowledge`: `KeyError: 'user_name'`.
- `test_hierarchical_ingestion`: `400 API key not valid` (`API_KEY_INVALID`).
- `test_telegram_webhook_success_flow`: `Expected ainvoke to have been awaited
  once. Awaited 0 times.` (mock obsoleto; ya corregido en esta reparación).

El test de `bienestar` no existe en `HEAD` (test y skill son trabajo local sin
seguimiento). Para demostrarlo sin la reparación se construyó un baseline
temporal con `HEAD` + los cambios locales del dueño, excluyendo los módulos y
tests de esta reparación; allí **5 failed**, incluido
`test_bienestar_skill::test_undo_...` con `AssertionError: assert True is False`.
Es decir, los cinco fallos existen sin el código reparado; ninguno se declara
reparado. La salida completa está en
`specs/002-reparacion-aegen/evidencia-preexistentes.md`.

Limitaciones de la evidencia: son pruebas con mocks/FakeRedis, no una ejecución
real del bot; no hay Redis ni Docker en el Mac, el puerto 8000 lo ocupa SENDA y
la clave de Google sigue inválida. La prueba de integración del webhook sí
ejercita el router con el manager mockeado. **El estado de la VM no está
verificado**: este agente no puede conducir la consola SSH del navegador; el
propietario debe ejecutar el bloque de lectura del §2 de `despliegue.md` y pegar
su salida. La validación real por Telegram está descrita en el §7 del **mismo**
`despliegue.md` y **no se ha ejecutado**; requiere autorización de despliegue y
la cuenta del bot.

El procedimiento único de verificación, respaldo, despliegue y rollback está en
`specs/002-reparacion-aegen/despliegue.md`; **no se ha ejecutado** y requiere
autorización expresa. El plan publica solo los archivos de esta reparación, sin
arrastrar los cambios locales de SENDA. No se inicia otro bot ni otro polling
con el mismo token.

## Riesgos residuales

- **Event loop bloqueado:** el latido de renovación es `asyncio`. Si el proceso
  queda bloqueado más de 60 s, no renueva, el cerrojo expira y otra tarea puede
  adquirirlo mientras la primera sigue trabajando. No se declara resuelto.
- **Pérdida de propiedad o fallo de Redis en la renovación:** se registra, se
  deja de renovar y no se re-adquiere. El procesamiento en curso continúa; otro
  proceso podría empezar tras el TTL y solaparse.
- **Cerrojo que nunca se libera:** la espera se acota y se reprograma, pero si
  el dueño sigue vivo y colgado, los reintentos se suceden. Los mensajes se
  conservan y su TTL se renueva mientras esperan; no se roba el cerrojo.
- **Recuperación al arrancar:** los buffers vivos se descubren con
  `SCAN ingest:buffer:*` y se procesan en segundo plano sin mensaje nuevo. Si
  Redis no está disponible al arrancar, no se recuperan; si la lista existe pero
  el contador expiró, se repara la secuencia. No hay garantía si Redis perdió
  las claves.
- **Ventana de reinicio:** un apagado ordenado extiende el TTL de los buffers
  pendientes a 3600 s. Un `SIGKILL` no ejecuta esa extensión y deja el TTL
  normal de 60 s. Si el reinicio supera la ventana, Redis descarta los mensajes;
  no es persistencia durable.
- **Apagado después de consumir el buffer:** si la cancelación llega tras
  `flush_all`, el lote ya se retiró de Redis y el procesamiento puede quedar
  incompleto. No hay reencolado transaccional ni replay; el test
  `test_lote_consumido_antes_de_apagar_no_se_recupera` demuestra que la
  recuperación devuelve 0 y no procesa. Es una limitación declarada, no resuelta.
- **Sin Redis real no hay buffer:** RF-7 cubre el camino del cerrojo cuando el
  buffer sigue disponible; el test usa `FakeBuffer`. Si Redis cae por completo,
  el buffer de ingesta no puede persistir los mensajes.
- **Dos instancias de la app:** el cerrojo Redis coordina mientras esté
  disponible; la degradación sin Redis no coordina entre instancias. El
  despliegue actual usa una sola instancia de `app`.

## Criterios de finalización

- Todos los RF con evidencia de test o lectura justificada.
- Tests nuevos y dirigidos en verde; fallos preexistentes registrados sin
  declararlos reparados.
- Recuperación de buffers al arrancar cubierta por test sin mensaje nuevo; el
  límite del lote ya consumido está probado y declarado, no oculto.
- Sin cambios en SENDA, sin secretos en logs/mensajes, sin despliegue.
- Informe final con: archivos tocados, comandos ejecutados y su salida
  relevante, bloqueos externos y comandos de despliegue no ejecutados.
- La validación real por Telegram no se declara cumplida hasta ejecutarla en la
  VM (con la salida del bloque de lectura §2 pegada por el propietario) y con la
  cuenta del bot; hoy es un bloqueo explícito, no un éxito supuesto.

## Disenso registrado

Vacío.

## Dudas abiertas

Ninguna bloqueante. La clave de Google válida sigue siendo un bloqueo externo
para embeddings nuevos; no impide cumplir la degradación de esta spec.
