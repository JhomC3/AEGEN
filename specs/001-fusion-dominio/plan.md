# Plan 001 — Fusión del dominio en AEGEN

Adopción del paquete preparado (`plan-fusion-funcional.md`); no se recrea desde
cero. Esta carpeta es la spec canónica. Base SDD armonizada conservada.

## 1. Línea base del recorrido afectado (AEGEN, observada 2026-10-04)

Carga: `SkillLoader.discover_and_load` (`src/personality/skills/*`, exige
`SKILL.md`, gating por env/paquetes/binarios) → `register_all_specialists`
(lifespan `main.py:60`) → `specialist_registry` (+ `CronScheduler`).
Routing: `enhanced_router` (no-texto→chat, sin herramientas→chat,
conversacional→chat, comando explícito→nodo, si no `RoutingAnalyzer` +
`_apply_routing_decision`; `_route_to_specialist` valida contra
`tool→specialist`, si no→chat) + `specialist_mapper` (preferido disponible, si
no→chat) + `intent_parser` (comandos `/tcc,/chat,…`, fast-path conversacional).
Ejecución: `SkillBasedSpecialist` (grafo un nodo `{id}_node`→END; args fijos
`user_message,chat_id,conversation_history,routing_metadata,rag_context` +
media; `async_capable`→worker, si no `tool.ainvoke`; sin tool→mensaje).
Respuesta: `graph_builder` (meta_router→context_retriever→specialist→
chain_router→next|END; `chain_to` o `respond_to_user`).
Brecha: sin autorización de chat en el recorrido (webhook acepta cualquier
`chat.id`; `AccessController` siempre `True`; `tcc` toca perfil/RAG/memoria sin
check). El dominio añadirá allowlist + check en borde y en herramienta.
Añadir especialista = `skills/<id>/SKILL.md` + `tools.py` (`SKILL_TOOL`, firma
async estándar) + (si comando) regex en `intent_parser` + (si intent nuevo)
patrones + fila en `mapper`; resto automático al arrancar.
Tests del recorrido: `test_skill_loader/parser/loader/gating/curator`,
`test_routing_intent_sync`, `test_vulnerability_routing`,
`test_conversational_flow`, `test_telegram_webhook`, `test_api_endpoints`.

## 2. Matriz de operaciones (contratos existentes; sin capacidades inventadas)

Leyenda: C=consulta, E=escritura. Preview/confirmación/undo según contrato
vigente. Rumbo vía API JSON aditiva (`api_rumbo.py`: mismos servicios y
snapshots que la UI) además de servicios. Aceptación = prueba contra backend
aislado + asserts listados.

| # | Dominio | Uso conversacional | Contrato | C/E | Datos | Preview | Confirmación | Undo | Aceptación |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Sesión | «qué entrené el <fecha>» | `GET /api/v1/sesion` | C | sets+rm, fecha ISO | — | — | — | vacío→`has_data:false`; error fecha→400; valores=DB |
| 2 | Sesión | «guarda hoy: Press 80×8» | `POST /api/v1/sesion` (reemplazo total) | E | día completo | diff día (series+rm) | sí explícita | journal `sesion` (10) | re-POST idempotente; validación 400 sin escribir; undo restaura |
| 3 | Diario | «qué comí el <fecha>» | `GET /api/v1/diario` | C | entradas+consumido+objetivo+parámetros | — | — | — | vacío→prefill marcado; 404 alimento no aplica aquí |
| 4 | Diario | «registra 50 g de avena hoy» | `POST /api/v1/diario` | E | día+parámetros | nutrientes recalculados servidor | sí | journal `alimentacion` | kcal half-up (50 g→195); 404 sin escribir; undo restaura filas |
| 5 | Alimentos | «kcal de 100 g de X» | `GET /api/v1/alimentos` | C | catálogo/100 g | — | — | — | 404 inexistente distinguido de 0 |
| 6 | Respiración | «mis sesiones de respiración del <fecha>» | `GET /api/v1/respiracion/sesiones` | C | sesiones+totales | — | — | — | vacío→`count:0`, no 404 |
| 7 | Respiración | «registra sesión 4/0/6/0 120 s» | `POST /api/v1/respiracion/sesion` | E | append por UUID | ciclos/BPM/fecha calculados | sí | sin journal; DELETE idempotente | re-POST→`saved:false`; 400 sin filas |
| 8 | Cardio | «mi cardio del <fecha>» | `GET /api/v1/cardio` | C | sesiones+anotación | — | — | — | vacío→`count:0` |
| 9 | Cardio | «anota cinta 10,5 km/h» | `POST /api/v1/cardio/anotacion` | E | upsert/borrado | efecto (crear/borrar) | sí | sin undo | vacío→`deleted:true`; hc ajeno→400 |
| 10 | Plantillas | «aplica mi plantilla X hoy» | `POST /api/v1/plantilla/aplicar` + `POST /api/v1/sesion` | E | preview→día | filas heredadas, descanso null | sí (al guardar) | vía sesión | día intacto tras preview; 404 id inexistente |
| 11 | Rumbo día | «mi rumbo de hoy / semana» | servicios `rumbo_simple_service` | C | yo/día/semana/52 sem | — | — | — | scores = suma (día /30, semana /210); sin persistir score |
| 12 | Rumbo día/yo | «hoy t1=8 t2=7 t3=9» | servicios `guardar_dia/guardar_yo` + snapshot undo | E | `rumbo_dia/rumbo_yo` | valores+score derivado | sí | snapshot undo existente | validación 1–10; undo restaura |
| 13 | Rumbo preguntas | «qué respondí a ex01» | servicios `vigente/historial` | C | respuesta+origen+fecha | — | — | — | vigente vs historial; origen chat/manual |
| 14 | Rumbo respuesta | «respondo ex01: …» | servicio `guardar_respuesta` + snapshot | E | `rumbo_respuestas` | texto+pregunta | sí | snapshot undo | 400 pregunta inválida sin escribir |
| 15 | Sugerencia/fechas | «qué me toca hoy» | `GET /api/v1/sugerencia`, `GET /api/v1/fechas` | C | rutina/pendiente/fechas | — | — | — | `rutina/descanso/nada` según cobertura; 400 fecha inválida |
| 16 | Undo | «deshaz lo último» | `GET /api/v1/undo/peek` + `POST /api/v1/undo` | E | top global | `kind/fecha` del peek | sí | consume 1 con backup | vacío→`kind:empty`; undo web/API coherentes |

Segundo corte (especificar antes de habilitar): `POST plantilla/guardar`,
altas ejercicio/alimento (409, sin undo), `DELETE sesion/diario/respiracion`,
plantillas-comida. No habilitar edición de metas, borrados o imports sin
contrato comprobado.

## 3. Decisión uno/dos procesos (marco + ensayo mínimo T4a)

Criterios: colisión `src`, dependencias (3.11 vs 3.13, lockfiles), lifecycle
(FastAPI docs cerrados vs app dominio con UI/htmx, migraciones al arrancar),
puertos (ambos 8000) y fallos (dominio caído ≠ orquestador caído).
Ensayo: copia de trabajo sin datos reales; importar dominio desde ubicación
destino candidata; arranque + 1 consulta + 1 escritura en DB aislada en cada
opción. Elegir la suficiente más simple sin `sys.path` permanente ni
dependencia al checkout viejo. Por defecto provisional: dos procesos en el
mismo proyecto (mismo código canónico, responsabilidades separadas) salvo que
el ensayo demuestre importación limpia en uno.

## 4. Orden de ejecución

T1 inventario y corte (hecho, ver spec) → T2 esta carpeta (diff antes de
conducta) → T3a gates con fallo real + T3b recorrido → T4a ensayo/decisión →
T4b transferencia y arranque desde destino con DB aislada → T5 consultas →
T6 escrituras por capacidad (matriz) → T7a aplicar SENDA (nombre aprobado) / T7b paridad y
Rumbo → T8a transferencia/rollback en aislado → T8b solo con autorización →
T9 veredicto RF×evidencia. Sin commits/push/merge/publicación ni datos vivos
sin autorización suficiente.

## 6. Despliegue definitivo en GCP (pendiente de autorización de corte)

Inventario base: VM `instance-20251218-164804` (`us-central1-a`,
`gen-lang-client-0656619648`), AEGEN en `/home/jjhonn_1020/AEGEN`
(`develop@1148766`), `docker-compose`, red `aegen_magi_network`, sanos
`magi_app_prod`/`magi_polling`/`magi_redis` (conservar polling; no duplicarlo).
Archivos tocados idénticos entre `1148766` y el HEAD local: el paquete aplica
limpio. Firewall GCP y backups, pendientes (`inventario-gcp.md`).

1. Transferir el paquete de producción (tar SHA abajo) a la VM por medio
   privado; verificar SHA-256 completo antes de extraer.
2. Extraer sobre `/home/jjhonn_1020/AEGEN` sin tocar contenedores vivos,
   `.env`/`.env.save`, `storage/` ni Redis.
3. `TS_AUTHKEY` (efímera + tag) directo en el host (`read -s`, `.env`, 600);
   nunca en el chat. `SENDA_SYNC_TOKEN`/`SENDA_CSRF_SECRET` operativos por el
   mismo medio.
4. `docker-compose -f docker-compose.yml -f ops/proxy/compose-senda.yml
   config` (revisar) y `up -d --build senda tailscale` (solo esos dos).
5. Serve por separado y persistente: `docker exec magi_tailscale tailscale
   serve --bg --https=443 http://127.0.0.1:8000`; verificar con
   `tailscale serve status`. Nunca Funnel.
6. Probar con el guion de `prueba-gcp-aislada.md` adaptado a definitivo
   (URL vigente `https://senda.tail402592.ts.net/`, credencial operativa,
   denegación no autorizada, consultas AEGEN, persistencia tras reinicio y
   recreación ordenada senda→tailscale).

## 7. Corte de datos (solo en ventana autorizada, móvil pausado)

1. Detener el escritor actual y comprobar que no quedan otros escritores.
2. Respaldo SQLite con `.backup` (WAL correcto); registrar integridad,
   esquema, conteos y hashes por tabla.
3. Copia recuperable fuera de la VM en destino existente autorizado
   (pendiente: indicar cuál; no crear buckets/servicios de pago).
4. Transferir respaldo + secretos por medio privado (nunca al chat ni en
   imágenes); `init_db` con backup previo a cualquier migración.
5. Arrancar SENDA definitivo; comparar origen/destino y justificar cada
   diferencia; mantener el origen detenido y recuperable; un solo escritor.
6. Rollback: reconciliar vía API cualquier escritura posterior al respaldo
   antes de restaurar; nunca backup antiguo encima.

## 8. AEGEN y móvil (pendiente)

1. Incorporar al AEGEN desplegado `senda_specialist` + `/senda` (alias
   `/bienestar` conservado) desde el paquete; reconstruir su imagen.
2. `BIENESTAR_DOMAIN_URL=http://senda:8000`, token y allowlist de Telegram vía
   `.env` del host, sin exponer valores.
3. Chat ID desde la instancia existente: el dueño escribe al bot y pega la
   línea `Iniciando orquestación para chat <id>` de
   `docker-compose logs app` (existe en `1148766`; sin bots de terceros y sin
   detener el polling).
4. Actualizar AEGEN con respaldo previo (imagen/container IDs anotados) y
   rollback = contenedor anterior; conservar configuración, `storage/`, Redis
   y especialistas.
5. App definitiva con URL HTTPS operativa; actualizar **sin desinstalar**
   (mismo `applicationId`, firma compatible, datos e identidades HC intactos).
6. Revisar borradores y colas pendientes antes de cambiar de servidor (no
   drenar a ciegas ni descartar en silencio); outbox con datos ficticios de
   prueba ya reconciliado según evidencia.

## 9. Validación y declaración (pendiente)

Lecturas reales (entreno/alimentación/Rumbo) desde móvil; escritura
controlada + lectura + reinicio + undo sin reaparición; Health Connect con
permisos y sync en dispositivo; Telegram → AEGEN → SENDA real con
autorización y respuestas fieles; reinicio/recreación + persistencia + HTTPS;
resto de especialistas y bot ok; recursos bajo uso representativo; respaldo y
recuperación del destino. Solo entonces declarar el escritor canónico.

## 5. Decisión T4a (2026-10-04, con evidencia)

**Dos procesos en el mismo proyecto.** Código canónico en
`apps/entrenamiento/`, ejecutado con su propio intérprete/venv y CWD; AEGEN
habla con el dominio por HTTP loopback (API v1 + `X-Sync-Token`), nunca por
import.
Evidencia: ambos usan paquete superior `src` con `from src.*` (colisión directa
en un intérprete); gates de AEGEN (async-first, 200 líneas, mypy estricto)
contaminarían el código sync transferido (RNF-02); `plotly` falta en el venv de
AEGEN; Python 3.11 vs 3.13 y lockfiles distintos. Alternativa descartada: un
proceso (exigiría fusionar `src/` o reescribir ~40 módulos + dependencias).
Android: fuente trasladada a `apps/entrenamiento/android/` (solo `app/src`,
`gradle/`, `*.kts`, `gradlew`; SDK/build/caches excluidos, ~1.4 MB);
el build lee `../data/hc_sync_token` y se re-apunta en T8b. Cambio de host
exige recompilar (URL en `BuildConfig`); mismo `applicationId`, sin desinstalar.

## 10. Despliegue del especialista en AEGEN GCP (preparado, no ejecutado)

Contenido necesario ya incluido en `senda-prod.tar` (skill `bienestar/`,
routing ×3, `config/base.py`, `routing_models.py`, `polling.py`,
`.env.example`; probado localmente: 21 + 36 tests, gates limpios).
En la VM, sobre `/home/jjhonn_1020/AEGEN` (rama `develop`, sin tocar
contenedores vivos hasta el momento):

```bash
tar -tf senda-prod.tar | head   # inspeccionar (solo lectura)
# extraer SOLO rutas AEGEN (excluye apps/, ops/, specs):
tar -xf senda-prod.tar src/personality/skills/bienestar \
  tests/unit/personality/test_bienestar_skill.py \
  src/agents/orchestrator/routing/intent_parser.py \
  src/agents/orchestrator/routing/intent_patterns_data.py \
  src/agents/orchestrator/routing/specialist_mapper.py \
  src/core/config/base.py src/core/routing_models.py src/tools/polling.py
docker-compose build app   # reconstruye con el skill (swap disponible)
```

Respaldo previo: anotar imagen/container ID actuales
(`docker ps`, `docker images`) para rollback = recrear anterior.
Actualizar = `up -d app` (polling se reconecta solo); rollback = imagen previa.
`BIENESTAR_*` y allowlist vía `.env` del host (valores nunca al chat).

## 11. Chat ID vía instancia existente (completado el hallazgo; pendiente aplicar)

Chat ID confirmado por logs (valor en poder del dueño, no persistido aquí).
Para aplicarlo en GCP, en la VM:

```bash
cd ~/AEGEN
grep -q '^BIENESTAR_ALLOWED_CHAT_IDS=' .env || printf 'BIENESTAR_ALLOWED_CHAT_IDS=<id-confirmado>\n' >> .env
docker-compose up -d app   # polling se reconecta solo; resto intacto
```

Sin otro polling, sin bots terceros. Tras el despliegue del skill, consulta
real por `/senda` desde el chat autorizado (debe responder) y desde otro
alcance (denegado); Telegram pendiente hasta entonces.
