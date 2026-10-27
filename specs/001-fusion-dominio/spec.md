# Spec 001 — Fusión del dominio de bienestar y dirección personal en AEGEN

Fecha: 2026-10-04. Tipo: estructural. Estado: spec canónica registrada en AEGEN;
origen preparado en `entrenamiento/.tmp/armonizacion-sdd/spec-fusion-funcional.md`
(2026-10-03), contrastado con evidencia actual el 2026-10-04. No se recreó el plan
desde cero: `plan.md` y `tasks.md` de esta carpeta adoptan el paquete preparado.
Nombre definitivo de producto: **SENDA**, elegido por el dueño el 2026-10-04.
El nombre visible de la aplicación y del subagente será SENDA. La decisión de
marca no autoriza cambios en rutas, DB, credenciales ni identidades persistentes.

Proceso: `sdd-kit/SDD_BOOTSTRAP.md`. Constituciones: `entrenamiento` y `AEGEN`
(`docs/constitution.md` respectivas). Corte de origen: `entrenamiento@fa72df0` (`dev`), reconciliado a `0e4203f` (merge feat/shell-comun 048 tras H10/H11; árbol limpio salvo conversación ajena sin seguimiento, sin colisiones con esta unidad). Aportes Rumbo
pendientes fuera del corte: `feat/rumbo@529e84d`, `feat/rumbo-sin-js@b43b984`
(H04 envíos disabled sin JS); no se presentan como incorporados.

## Objetivo

Incorporar la aplicación actual de Entrenamiento (entrenamiento, alimentación,
respiración y Rumbo) a AEGEN como dominio gestionado por un subagente propio,
con código canónico dentro de AEGEN, sin importar código ni assets del checkout
anterior en runtime. No basta una conexión permanente entre checkouts.

## Contraste con evidencia actual (2026-10-04)

- Dominio verificable: contratos API v1 (sesión, diario, alimentos, plantillas,
  cardio, respiración B5, fechas B4, sugerencia), `X-Sync-Token` con
  `compare_digest` y fallo cerrado, CSRF exento por igualdad exacta, gate LAN con
  allow-list método+path, backups pre-mutación + undo máx 10 (`mutation_service`),
  idempotencias (re-POST, DELETE doble, UUID respiración, `hc_id`+`revision` en
  sync). Único SQL en `db_*.py` vía `db_connection` (WAL, `busy_timeout=5s`).
- Rumbo implementado y probado: `rumbo_yo`/`rumbo_dia`/`rumbo_respuestas`,
  36 preguntas, scores derivados no persistidos, CRUD solo HTML/htmx
  (`ui_rumbo`: `GET /rumbo`, `POST /rumbo/yo|dia|respuesta`,
  `GET /rumbo/pregunta/{id}`) con backup+undo; **sin API JSON**. Tests unitarios,
  de rutas y e2e existen.
- AEGEN verificado: `SkillLoader` (SKILL.md + `SKILL_TOOL`), registro diferido,
  `SkillBasedSpecialist` (grafo un nodo, args fijos, `chain_to`), routing
  (comandos explícitos, intents, validación contra especialistas disponibles,
  fallback chat). **Brecha de autorización**: webhook Telegram sin allowlist de
  chats; `AccessController.validate_global_access` siempre `True`; el dominio
  exigirá allowlist + check en borde y en herramienta.
- Bloqueo demostrado: `Makefile:lint` ignora mypy (`-`), `Makefile:test`
  convierte el fallo en mensaje (`|| echo`), `addopts` con `--no-cov` y 2
  excludes históricos. `verify` no propaga fallos reales (RF-09/T3a).
- Puertos/entorno: ambos declaran 8000; hoy sin listeners. Python `>=3.11` vs
  `>=3.13`; compatibilidad de lockfiles pendiente de ensayo (T4a). `src` en
  ambos proyectos: prohibido superponer carpetas o hacks permanentes de
  `sys.path`. Decisión uno/dos procesos pendiente de ensayo (ver `plan.md`).
- Datos vivos excluidos de pruebas modificables: `data/*.db`, backups, tokens
  y secretos (gitignored). Android/Health Connect: `applicationId`
  `com.jhomc.healthsync`, `DEFAULT_SYNC_TOKEN` desde `data/hc_sync_token`,
  `hc_id`/`clientRecordId`/`revision`/`record_type` estables; no cambian con el
  renombre.

## Requisitos (adopción de RF-01–RF-14 del paquete preparado)

- RF-01 Incorporación: código canónico del dominio dentro de AEGEN, operable sin
  el checkout anterior; procedencia/historia trazables. Uno o dos procesos es
  decisión técnica documentada, no dos productos.
- RF-02 Subagente: delegación por mecanismo existente (skill registrada);
  comando explícito y delegación natural a las mismas operaciones; demás
  especialistas intactos.
- RF-03 Paridad: capacidades de entrenamiento, nutrición, cardio, respiración,
  plantillas, métricas, backups, undo, sync y Rumbo del corte verificado;
  sin rediseño visual salvo renombre acordado.
- RF-04 Acceso independiente: app directa utilizable sin orquestador ni LLM;
  caída del dominio contenida sin inutilizar otros especialistas.
- RF-05 Consultas: valores, fechas y unidades desde la fuente del dominio;
  distinguir vacío/error/cero; sin memoria conversacional como sustituto.
- RF-06 Escrituras: preview concreto + confirmación, validación y persistencia
  del dominio, sin cambios no solicitados, éxito solo tras persistencia
  comprobada, backup/undo según contrato.
- RF-07 Concurrencia/repetición: sin sobrescrituras silenciosas ni duplicados;
  reconciliar antes de repetir; confirmación vieja no autoriza otra operación.
- RF-08 Autorización: denegar antes de operar sin autorización; auth, red y
  secretos preservados; credenciales fuera del LLM y de logs.
- RF-09 Correcciones AEGEN: solo deficiencias que bloqueen integración o su
  verificación, con reproducción y regresión; gates con fallo real; exclusiones
  con estado y causa. Sin reescritura general.
- RF-10 Datos/transición: solo con autorización operativa; backup consistente,
  integridad comprobada, un solo escritor canónico; sin migraciones
  concurrentes ni copias editables divergentes.
- RF-11 Recuperación: procedimiento probado antes del corte; sin restaurar
  backup antiguo perdiendo escrituras posteriores.
- RF-12 Rumbo paralelo: ramas/worktrees preservados, corte registrado,
  reconciliación de aportes autorizados; rama pendiente ≠ incorporada.
- RF-13 Renombre: aplicar **SENDA** a la marca visible y al subagente, sin tocar
  rutas API, DB, credenciales ni IDs persistentes. Nombre decidido; implementación
  y validación del renombre todavía pendientes.
- RF-14 Errores/fechas: reloj y zona configurados o aclaración; resultado fiel;
  consultas sin escrituras; sin URLs/métodos arbitrarios del LLM.

## Fuera de alcance

Reescritura general de AEGEN; rediseño visual; Rumbo nuevo no especificado;
recomendaciones médicas o promesas de felicidad; publicación, commits, merges,
mensajes reales, parada de servicios ajenos, cambios en datos vivos y retirada
del origen sin autorización suficiente. Preparar ≠ ejecutar.

## Finalización

RF-01–RF-14 con evidencia individual; app incorporada arrancable desde destino
y subagente con consultas/escrituras habilitadas probadas; regresión de
capacidades y especialistas; app directa sin LLM; datos reconciliados y
recuperación validada (o procedimiento revisable si falta corte); Rumbo
reconciliado con precisión; RF-13 cumplido solo tras aplicar y validar SENDA; sin corte operativo se
declara implementación local pendiente de transferencia, nunca «fusión completa»;
origen retirado como escritor solo tras corte autorizado.

## Escritor actual identificado (2026-10-05, con evidencia)

- Escritor de datos reales en este Mac: PID 24559, CWD
  `/Users/jhomc/Proyectos/AEGEN/apps/entrenamiento`, escucha `:8000`,
  `/healthz` 200. Es el destino provisional con la DB transferida
  (`apps/entrenamiento/data/lifestyle.db`); el checkout origen está detenido.
- Incidente 2026-10-04 14:17 (causa propia, ya remediado): una prueba del flujo
  de secretos ejecutó el script real contra `data/` y sobrescribió
  `hc_sync_token`/`csrf_secret` con valores de prueba. Detectado por tamaño y
  fecha; restaurados byte-idénticos desde el origen (origen intacto);
  servidor reiniciado limpio (`healthz`/`api` 200, cero fugas en log).
  Lección registrada: probar scripts con `cd` parcheado a sandbox, nunca
  contra el árbol operativo.

## Despliegue GCP existente (inventario, 2026-10-04/05)

- VM `instance-20251218-164804`, zona `us-central1-a`, proyecto
  `gen-lang-client-0656619648`. AEGEN en `/home/jjhonn_1020/AEGEN`, rama
  `develop`, HEAD `1148766`; `docker-compose`, red `aegen_magi_network`;
  sanos `magi_app_prod`, `magi_polling`, `magi_redis` (el polling existente
  se conserva; no iniciar otro).
- Persistencia: `.env` del host, `storage/`, volumen Redis. `.env`/`.env.save`
  con 600; `.env.save` es ajeno y no se incorpora.
- VM: 975 MiB RAM (333 MiB libres en captura), swap en uso, 11 GB libres.
  Tailscale no instalado (va en contenedor). Firewall GCP y backups,
  pendientes de comprobar.
- Sin acceso gcloud/docker/ssh desde este Mac: el inventario vivo lo ejecuta
  el dueño con el guion de `inventario-gcp.md`.

## Evidencia del entorno de prueba GCP (comunicada, no reejecutada aquí)

- Móvil → SENDA por HTTPS privado + token; guardar/leer/reiniciar/undo;
  día vacío 60 s navegando; reinicio de ambos contenedores conserva datos,
  credenciales y Serve; recreación ejecutada por el dueño (sondeo vencido por
  `uv run` instalando 18 dev-deps: corregido con `UV_NO_SYNC=1`, pendiente
  re-recrear); consulta desde `magi_app_prod` a `senda-test` 200; medición
  104.3 + 29.57 MiB con 220 MiB libres.
- Android: reconciliación de borrador en memoria sin fila persistente;
  21 pruebas relevantes; app separada `com.jhomc.healthsync.sendatest`;
  datos ficticios (`SENDA PRUEBA`, `2001-01-02`).
- Pendientes: recreación con la configuración corregida, denegación no
  autorizada, recuperación/backups externos, datos reales, HC, Telegram.

## Disenso y pendientes

### Regresión móvil durante prueba GCP (2026-10-04)

Alcance localizado de RF-07/RF-14: reconciliar también el borrador en memoria
cuando no existe una fila en `entreno_drafts`. Si el contenido remoto difiere
de la última copia confirmada, descartar ese borrador y su escritura pendiente
antes de drenar. Si no hay lectura válida o el servidor no cambió, conservarlo.
Un 429 conserva la cola y detiene el drenado, sin confirmar ni descartar operaciones.
Aceptación: prueba con Room y HTTP simulado de sesión guardada → servidor vacío
por undo → reconciliación sin POST, borrador invalidado y cola intacta/vacía según
corresponda; controles de servidor sin cambios y de lectura fallida. Compilar la
app de prueba separada y validar posteriormente con dispositivo/GCP.
Evidencia disponible: el backup móvil tiene cola vacía, sin borrador del día 3,
pero caché con la serie guardada. La entrada 4 en GCP demuestra otra escritura,
no identifica por sí sola su desencadenante. No atribuir esa escritura a la cola
sin reproducción. Sin modificación del origen ni datos operativos ni commits.

Validación local: Room + MockWebServer reprodujeron el fallo sin fila persistente
antes de la corrección. Después: 21 tests (reconciliación 3, drenado 5, borradores
3, feedback 10), sin fallos; APK debug compilada. El 429 ya conservaba la cola
según la prueba existente: no se modificó ese comportamiento. Corregido solo el
caso de memoria sin fila local. Pendiente validación real GCP/móvil; no se declara
explicado el desencadenante exacto de la entrada 4 ni resueltos todos los casos
de concurrencia del outbox móvil.

- [Implementación] SENDA aplicado en marca y subagente (RF-13 ejecutado;
  pendiente validar renombre en dispositivo y Telegram).
- [Operativa] Corte GCP, retiro del origen, Git y publicación: pendientes de
  autorización específica. Decisión registrada: dos procesos, ubicación
  conjunta en GCP.

## Configuración definitiva registrada (nombres, URL, volúmenes, secretos)

- Nombres: servicio `senda` (`senda_domain`), red `magi_network` existente,
  volúmenes `senda_data` + `tailscale_state`; test usa `senda-test`,
  `senda_test_domain`, `senda_test_tailscale`, `senda_test_data`.
- URL definitiva: `https://senda.tail402592.ts.net/` (serve HTTPS tailnet,
  sin funnel/público). AEGEN interno: `http://senda:8000`.
  `BIENESTAR_DOMAIN_URL` por entorno (loopback Mac hoy, `senda:8000` en GCP).
- Volúmenes: `senda_data:/app/data` (SQLite+backups). Sin instalaciones
  duplicadas: deps en build (`uv sync --locked --no-dev`), `UV_NO_SYNC=1`
  en runtime.
- Secretos: `.env` del host (600, gitignored) → `SENDA_SYNC_TOKEN` /
  `SENDA_CSRF_SECRET` explícitos al contenedor (sin `env_file` general);
  `start_server.sh` persiste a `data/` sin imprimir. Rotación: sustituir en
  `.env`, recrear, rebuild APK, actualizar AEGEN, 401 al viejo.
- Android: cambio de host **exige recompilar** (`DEFAULT_SYNC_URL` en
  `BuildConfig`); mismo `applicationId`, misma firma (no desinstalar),
  token sin cambios. App de prueba separada `com.jhomc.healthsync.sendatest`
  solo para el entorno de prueba.

## Evidencia comunicada por el dueño — GCP y móvil (2026-10-04)

- Red privada HTTPS y token: móvil llegó a API; navegador sin token rechazado.
- Guardado 10 kg / 9 reps / RIR 2 verificado por lectura de API y por el móvil
  tras reiniciar app. Undo esperado consumido; día vacío durante 60 segundos
  con app navegando; volvió propuesta 10/8/2 sin escritura. Prueba focalizada,
  no garantía de todos los casos del outbox. Desencadenante de entrada 4 no probado.
- Reinicio de ambos contenedores: sesión testigo 2001-01-02 intacta, día de undo
  vacío, token válido y Serve HTTPS privado conservado. Recreación no probada aún.
- Consulta HTTP desde magi_app_prod al DNS senda-test:200 con token y ejercicio
  ficticio confirmado. No equivale a routing del especialista ni Telegram.
- Medición puntual: dominio 104.3 MiB + Tailscale 29.57 MiB; disponibles 220 MiB,
  swap usada 706 MiB. No demuestra capacidad bajo carga ni coste cero.
- Canonicalizados los arreglos comprobados en VM: Dockerfile bash, contexto
  relativo correcto, sin env_file general, containerboot con userspace/auth-once,
  digest Tailscale fijado y Serve configurado separadamente con persistencia.
- Pendientes: recreación, denegación desde identidad no autorizada, recuperación
  GCP/backups externos, datos reales y corte definitivo, permisos HC, Telegram
  y publicación del código nuevo. No declarar fusión completa.

Recreación ejecutada por el dueño: el sondeo de 60 segundos venció; los registros
posteriores muestran dominio healthy, Tailscale autenticado y peticiones del
móvil con 200. Causa de demora observada: `uv run` sincronizó 18 dependencias de
desarrollo al arrancar (63 segundos solo en instalación). Dockerfile y Compose
ahora fijan UV_NO_SYNC=1 tras preparar el entorno durante el build. Pendiente
recrear con esa configuración, verificar sin descargas y revalidar los testigos.
