# Tareas 001 — Fusión del dominio en AEGEN

Adopción de `tasks-fusion-funcional.md` (origen en `entrenamiento/.tmp/`).
Unidades verificables, no ramas separadas; fases secuenciales reutilizan rama
y directorio. Sin commits sin autorización suficiente.

- [x] T1. Inventario, corte de origen y protección de datos/trabajo ajeno.
  (RF-03, RF-08, RF-10, RF-12) Hecho cuando: HEAD/diffs/worktrees/procesos/
  puertos y activos identificados; DB viva excluida; Rumbo pendiente registrado.
  Evidencia: este spec (contraste 2026-10-04) + informes de exploración.
- [x] T2. Spec/plan/tasks canónicos + línea base + matriz. (RF-01–RF-14)
  Hecho cuando: esta carpeta existe con alcance total y matriz §2; diff
  mostrado antes de conducta. Nombre SENDA aprobado por el dueño el 2026-10-04.
- [x] T3a. Propagación de fallos de validación de AEGEN. (RF-09)
  Hecho cuando: test/tipos fallidos devuelven código no cero; exclusiones con
  causa/estado; sin bajar controles ni borrar tests.
- [x] T3b. Recorrido de subagente y regresión. (RF-02, RF-09)
  Hecho cuando: carga→routing→herramienta→respuesta comprobado; especialistas
  existentes con regresión pertinente; cada arreglo responde a fallo demostrado.
- [x] T4a. Ensayo imports/dependencias/lifecycle; decisión uno/dos procesos.
  (RF-01, RF-04) Hecho cuando: decisión con evidencia y alternativa; sin
  colisión `src` ni dependencia al checkout viejo.
- [x] T4b. Transferencia y arranque desde destino con DB aislada.
  (RF-01, RF-03, RF-12) Hecho cuando: app arrancable desde AEGEN, sin runtime
  al árbol viejo; vivos excluidos.
- [x] T5. Subagente + consultas autorizadas 4 dominios. (RF-02, RF-05, RF-08,
  RF-14) Hecho cuando: comando + natural consultan datos reales; fechas/
  errores/permisos probados; consultas sin escrituras.
- [x] T6. Escrituras especificadas (§2 ops 2,4,7,9,10,12,14,16). (RF-06–RF-08)
  Hecho cuando: preview+confirmación vinculados, persistencia y undo probados,
  sin pérdida ni duplicados.
- [x] T7a. Aplicar y validar **SENDA** en la marca visible y el subagente. (RF-13)
  Nombre elegido por el dueño el 2026-10-04; no cambiar rutas API, DB,
  credenciales ni IDs persistentes. No marcar hecho hasta validar el renombre.
- [x] T7b. Paridad, fallos contenidos y Rumbo. (RF-03, RF-04, RF-12)
  Hecho cuando: mismas fixtures compatibles; app directa sin LLM; Rumbo
  reconciliado al corte.
- [x] T8a. Transferencia y rollback en aislado (procedimiento). (RF-10, RF-11)
  Hecho cuando: backup consistente, un escritor, integridad y recuperación
  probados; procedimiento presentado sin ejecutar corte.
- [ ] T8b. Corte operativo solo con autorización. (RF-10–RF-13)
  Sin autorización/dispositivo: declarar pendiente, no cumplido.
- [ ] T9. Veredicto RF×evidencia y cierre. (RF-01–RF-14)
  Hecho cuando: resultados, pruebas, límites, pendientes y autorizaciones
  documentados; ninguna fase parcial como fusión completa.

## Cobertura por operación (dictamen 2026-10-04, verificado)

Consultas: sesion, diario, respiración, cardio, rumbo-día, sugerencia,
alimento (catálogo), rumbo-preguntas/historial, plantilla-preview. Todas con
pruebas (mock + vivo) y sin escrituras.
Escrituras con preview+hash+confirmación: sesion (añadir conserva,
reemplazo declarado), diario (añade conserva), respiración (fecha/epochs
deterministas, UUID idempotente), rumbo-día (atómico 409), rumbo-respuesta,
cardio-anotación (upsert por clave), undo (huella precisa + declaración
explícita), plantilla-aplicar es solo preview (guardar va por op sesion).
Segundo corte pendiente: plantilla-guardar, altas, deletes, fechas.

## Correcciones del dictamen (undo atómico, transferencia, SENDA)

- U1 Undo exacto: `peek` devuelve `entry_id`; `POST /api/v1/undo` acepta
  `{"expected": {"id", "kind"}}` y lo comprueba+consume en una transacción
  con `BEGIN IMMEDIATE` (409 intacto ante otra escritura, mismo tipo o no).
  Restore con re-inserción del mismo id ante fallo. Cliente: preview guarda
  `expected`, confirmación lo envía; cualquier error de verificación aborta
  sin POST; mensaje honesto sobre precisión (huella propia vs confirmada).
  Tests: `test_undo_expected.py` (3) + skill (lectura-falla, 409 mismo tipo).
- U2 Transferencia: parar-antes-de-backup, reconciliación final, ensayo de
  recuperación como precondición; Android-fuente incorporado; 97 tests;
  `BIENESTAR_DOMAIN_URL=http://127.0.0.1:8000` loopback definitivo.
- U3 SENDA aplicado: marca visible (6 plantillas + README), subagente
  `senda_specialist` (`/senda`, alias `/bienestar`), loader+routing
  verificados, 216 tests de marca en verde. Rutas/DB/credenciales/IDs intactos.

## Transacción única de undo (dictamen 2026-10-04, verificado)

- U4 Undo monotransacción: verificar (id+kind), restaurar y consumir en una
  sola transacción `BEGIN IMMEDIATE` sobre la misma conexión
  (`_use_conn` en escrituras, restauraciones, diario y undo). Fallo en
  cualquier punto revierte todo: sin cambios parciales, entrada conservada.
  Tests: escritura intercalada durante el restore (sobrevive + queda
  registrada), fallo de restore sin cambios (DB y pila intactas),
  `test_undo_splits_restore_fallido` adaptado a la firma con `conn`.
  Dominio completo sin e2e: 961 passed.

## Snapshot dentro del bloqueo (dictamen 2026-10-04, verificado)

- U5 Captura anterior en la misma transacción: los 4 wrappers capturan
  `before` con la misma conexión tras `BEGIN IMMEDIATE`
  (`get_sets_by_fecha`, `get_diario_by_fecha`, `get_parametros_diarios`,
  `snapshot_rumbo_simple` aceptan `conn`). Una escritura concurrente espera
  fuera y su snapshot posterior ya incluye el cambio: al deshacerla no
  resucita datos (probado: 9/9/9 intercalado sobrevive y su undo deja vacío).
- U6 Fallo tras modificar revierte todo: restore roto a mitad revierte datos
  y conserva la entrada (misma id en la cima).
- Dominio completo sin e2e: 961 passed (ruff/format/mypy limpios).

## Regresión post-DELETE + origen e9ee8ab (verificado)

- U7 Falla-después-de-borrar como regresión persistente
  (`test_undo_expected_fallo_tras_borrar_revierte_todo`): filas y cima intactos.
- U8 Origen en `e9ee8ab` reconciliado (H06+H09 aire vertical; diffs restantes
  solo marca SENDA, asserts de nuevos campos y adiciones de fusión).
  Suite destino sin e2e: 962 passed. Corte operativo T8b preparado, no ejecutado.

## Topología GCP (dirección aceptada, despliegue no autorizado)

- U9 Allow-list remota: 6 rutas JSON de Rumbo añadidas (el subagente es peer
  no-loopback); test `test_rutas_subagente.py` cubre las 20 rutas usadas.
- U10 Artefactos preparados: `Dockerfile` del dominio, fragmento compose
  (`senda` sin puertos + `proxy` Caddy 443), `Caddyfile`, recorridos
  AEGEN/móvil/navegador, migración y rollback. Android exige recompilar al
  cambiar de host (URL en `BuildConfig`).
- Pendiente: inventario vivo de GCP (sin acceso desde este Mac), despliegue,
  corte Mac→GCP, móvil y Telegram contra GCP.

## Tailscale HTTPS + secretos sin volcado (verificado)

- U11 `tailscale serve --bg https://:443 http://senda:8000` (TLS de la propia
  tailnet, sin funnel/público); Android solo cambia URL (HTTPS válido, sin
  tocar network-security-config). Clave reutilizable (nodo no efímero) +
  tag `senda`; verificar tags y grants antes de desplegar. Compose actualizado.
- U12 `start_server.sh`: fuente única (env explícito → fichero → generar),
  cero impresiones de valores (probado: reutiliza/env/genera). Rotación
  documentada. Entrypoint verificado con secretos por env en DB aislada (200).

## Ciclo arranque/reinicio/rotación probado (datos aislados, 2026-10-04)

- Arranque con secretos por env (mecanismo del despliegue): 200.
- Reinicio: reutiliza ficheros (SHA idéntico), 200.
- Rotación (sustituir fichero + rearrancar): nuevo 200, viejo 401.
- Artefactos retirados. Nombres/fuente unificados Compose↔script
  (`SENDA_*`, `.env` raíz documentado en `.env.example`).

## Serve vigente + entrypoint probado (2026-10-04)

- U12 Sintaxis vigente verificada en docs oficiales (`serve [flags] <target>`):
  `serve --bg --https=<puerto> <destino>`; proxy solo admite `http://127.0.0.1`,
  de ahí `network_mode: service:senda` (backend por loopback real) y AEGEN
  intacto por `magi_network`. `--bg` persiste tras reboot (`serve status`).
- U13 Entrypoint sin `sleep` fijo: espera `tailscale status` con tope,
  verifica `serve status --json` y falla (exit 1, restart) si no hay serve.
  Probado con stubs: 2 fallos→ready→serve exacto→verificación OK; nunca-ready
  → tope→«serve no activo»→exit 1. Artefactos retirados.
- U14 Compose validado por parseo (2 servicios, senda sin puertos, volúmenes,
  env con fail-fast `${VAR:?}`); `bash -n` OK. Sin Docker/Tailscale/GCP aquí:
  build, serve real, ACL efectiva y recursos se prueban en GCP con datos
  aislados (pendiente).

## Prueba GCP aislada reescrita (pendiente de ejecución en la VM)

- U16 Proyecto exclusivo `senda-test` en `~/senda-test` (directorio, nombres,
  volúmenes y `docker-compose` explícitos en cada comando; red externa
  `aegen_magi_network` solo adjuntada). Secretos 600 desde la creación.
  Salud por contenedor/URL privada (nunca puerto 8000 del host), API completa
  con token sin mostrarlo, consumo real, denegación tailnet no autorizada
  (con ACL de ejemplo), persistencia tras reinicio y recreación ordenada
  senda→tailscale, limpieza limitada a recursos senda-test. Bundle senda-prod.tar SHA d8931ae5 (334 entradas).

## Prueba GCP aislada (pendiente de ejecución en la VM)

- U15 Bundle `.tmp-gcp/senda-prod.tar` (SHA 9e7ef101 entonces vigente, 334 entradas, sin
  secretos/pycache/data) + guion `prueba-gcp-aislada.md`: capacidad, secretos
  de prueba, arranque, HTTPS autorizado/denegado, consultas como AEGEN,
  persistencia tras reinicio, recreación senda→tailscale (dependencia netns),
  limpieza total. Archivos base idénticos entre 1148766 (GCP) y 8d1f671
  (local): sin conflictos para los ficheros tocados.

## Guion GCP cerrado (U17, pendiente de ejecución)

- U17 `config --quiet` sin secretos, HTTPS por nombre MagicDNS sin `-k`,
  salud/API internas desde Docker, HTTPS/API desde dispositivo tailnet (sin
  suponer red del host), testigo persistente tras reinicio Y recreación,
  SHA-256 completo pre-extracción (d8931ae5…c96), costes verificados nulos
  (sin IPs estáticas, LB, SQL ni buckets nuevos).

## Despliegue definitivo GCP (pendiente de autorización de corte)

- [ ] D1. Transferir `senda-prod.tar` (SHA-256 completo
  `5ee73d94452b5bd807f209ab0f61321f25ba5ffbfb9ffefb94c2c5`,
  `.tmp-gcp/`, 330 entradas, 0 prohibidas) a la VM por medio privado;
  verificar SHA-256 completo antes de extraer sobre `/home/jjhonn_1020/AEGEN`
  sin tocar vivos, `.env`/`.env.save`, `storage` ni Redis.
- [ ] D2. `TS_AUTHKEY` + secretos operativos directo en el host (nunca al chat).
- [ ] D3. `config` + `up -d --build senda tailscale` (solo esos dos);
  serve por separado y persistente; verificar `serve status`.
- [ ] D4. Pruebas §6 del plan con URL definitiva y credencial operativa;
  denegación no autorizada (o pendiente explícito sin segundo dispositivo).
- [ ] D5. Corte §7 en ventana autorizada con móvil pausado; un solo escritor.
- [ ] D6. AEGEN + móvil §8 (chat ID vía logs existentes, backup/rollback,
  APK sin desinstalar, borradores/colas revisados).
- [ ] D7. Validación §9 y declaración del canónico; T9 cierre.
- Pendientes externos: firewall GCP, backups/GCS, destino de respaldo fuera
  de la VM, DNS innecesario (tailnet), dispositivo real, Telegram completo.

## Corte 0e4203f reconciliado (Lote 048 + H10/H11)

- U18 Cambios e9ee8ab..0e4203f (047 movil-legible + 048 shell-común):
  7 archivos idénticos a la base → copia directa; `splits.html` reconciliado
  a mano (cambio H08 origen + marca SENDA, sin pisar); specs/047+048 y 2 e2e
  nuevos incorporados. Adiciones SENDA intactas (atomicidad, api_rumbo, marca,
  Android, exempts).
- U19 Evidencia: budget + split-routes + freeze + shell-común (37 passed) y
  movil-legible e2e (14 passed) en destino.
- U20 Paquete `senda-prod.tar` reconstruido (SHA
  `f4c11fedfab6834c945a3000b692bd23bd3f0b0f6b2152acfd679d7bc3f9c3df`,
  349 entradas, 0 prohibidas). El SHA anterior ya no afirma origen vigente.

## Paquete y corte 0e4203f (verificado 2026-10-05)

- U21 Paquete `senda-prod.tar` (SHA `f4c11fed…c3df`, 349 entradas):
  verificado por extracción: `splits.html` (marca SENDA + H08),
  `test_frontend_budget.py` (114K/248K), `specs/047+048`, `api_rumbo.py`
  byte-idénticos al árbol; 0 prohibidas (data/secretos/pycache/SDK/._*).
- U22 Backup nuevo del escritor en reposo (destino Mac caído tras reinicio
  del entorno; origen detenido; solo ajeno en 57042, intacto):
  `data/backup-pre-corte-20261005-mac.db`, SHA
  `15d1c51740cdffb5b93592b8486018d480a07c31eda91f0e610e791f80a74376`,
  integrity ok, esquema 24, conteos 1501/3087/21/0/36/9/29/67.
  Copia fuera de la VM pendiente de destino designado.
- Rollback vigente (`transferencia.md`): reconciliar vía API lo posterior al
  respaldo antes de restaurar; nunca backup antiguo encima.

## Respaldo externo y rollback sin API (2026-10-05)

- U23 Copia en `/Users/jhomc/Proyectos/respaldos-senda/20261005/` (SHA
  idéntico verificado, + `LEEME.txt`); SHAs completos de respaldo y paquete
  en `transferencia.md`. Rollback sin API: comparar, re-aplicar posteriores,
  rearrancar origen, verificar, declarar. SENDA detenido y fuera de servicio.

## Rollback sin API ensayado (U24) + corte preparado

- U24 Ensayo aislado superado: altas (ejercicio), modificación, borrado
  (anula su alta; journal lo registra), Rumbo día+respuesta; detección por
  tablas/journal; restauración en limpio + re-aplicación en orden; igualdad
  total (auditoría aparte); undo funcional; backup y viva intactos
  (SHA antes/después). Scratch retirado.
- Corte pendiente de ventana: parar escritor, backup+SHA/conteos, copia
  externa designada, transferencia privada, init, arranque, equivalencia,
  SENDA provisional→canónico solo tras móvil/HC + Telegram en vivo.

## Pre-corte verificado (2026-10-05, a la espera de «comenzar ahora»)

- U25 Ambos escritores detenidos (8000 libre; solo ajeno en 60166, intacto).
  DB vs respaldo: contenido idéntico en 10 tablas (SHA de fichero difería
  solo por metadatos WAL). Respaldo nuevo `backup-pre-corte-20261005-mac2.db`
  con SHA idéntico al validado `15d1c5174…0789`; copiado al destino acordado
  `respaldos-senda/20261005/`. Corte NO ejecutado (falta confirmación).

## Validación móvil en vivo, destino Mac (2026-10-05, U26)

- U26 Lectura (diario con entrenos reales), escritura controlada (serie 1:
  8 reps + descanso, RM 130.8 servidor) + lectura posterior, undo vía API
  (restaura 7 reps exactos, pila a #392, sin residuos; app mostraba caché
  hasta re-entrar al día). Sync manual: reporte #6 (29 tipos, 4107
  entregados, 0 fallos, 111 en cuarentena "sin registro local" por diseño).
- Brecha móvil: sin botón visible de undo (solo «Reiniciar entrenamiento»);
  contrato B1 preveía botón. No bloqueante (undo API verificado).

## Validación móvil/HC en provisional + estado pre-corte GCP (2026-10-05)

- U27 Móvil/HC validados en destino provisional (lectura, escritura
  controlada + undo exacto, sync reporte #6: 29 tipos, 4107 entregados,
  0 fallos). Cuarentena 111 = `sin registro local` (diseño: registros HC sin
  correspondencia local). Limitación de refresco: la app muestra caché hasta
  re-entrar al día (verificado). GCP y Telegram pendientes.
- U28 Escritor actual: SENDA Mac (PID verificado, `:8000`, sano). Escrituras
  posteriores al respaldo: training_sets +12 (sync), undo rotado por tope
  (prueba propia), sync_reports +1. Corte GCP exige respaldo nuevo tras
  parada; transferencia solo en ventana acordada con móvil/HC pausados.

## Incidente Telegram «hola» (U29 cerrado como no reproducido)

- El «hola» inspeccionado terminó correctamente (`error_message=None`,
  `sendMessage` OK). Sin causa atribuida; no se declara patrón ni corrección.
- Chat ID confirmado por logs (valor en poder del dueño, no persistido en
  docs): allowlist = ese ID vía `BIENESTAR_ALLOWED_CHAT_IDS` en el `.env` del
  host GCP. No se crea `ADMIN_CHAT_ID` (mínimo privilegio: sin token admin).
- Comando en la VM (sin mostrar valores): añadir la línea con el ID al `.env`,
  recrear `app` (`up -d app`; polling se reconecta solo), probar `/senda`
  desde el chat autorizado y uno no autorizado (denegado).

- Chat ID: ya obtenido del mismo log (línea `Iniciando orquestación para
  chat <id>`); configurado como allowlist (ver sección U29 cerrada arriba).
  Corte supeditado a móvil/HC pausados; tras despliegue, consulta real por
  `/senda`; Telegram pendiente hasta validarlo.

## Bloque ejecutable VM entregado (pendiente de ejecución)

- U18 Bloque único con `docker-compose`: preflight, respaldo config+imágenes
  en `~/.aegen-respaldo-<ts>`, SHA + extracción del tar, secretos idempotentes
  (ID solo en `.env` operativo, nunca en docs), `config --quiet`, build
  `senda`+`app` (sin recrear app: activación en el corte), up solo
  senda+tailscale, serve por separado + verificación, salud, rollback
  concreto (stop/rm/volúmenes + `.env` + checkout/clean acotados).
  Activación AEGEN→SENDA coordinada con el corte, no antes.

## Harness de scripts (bugs reales encontrados por prueba, U20)

- U20a `|| true` tragaba el aborto del filtro del tar → forma `if/grep -q`.
- U20b `set -e` + `S1=$(grep...)` sin coincidencias mataba el script →
  `return 0` en `gettok`.
- U20c `unset ALLOWLIST` prematuro borraba el ID de entorno → movido al final.
- U20d Manifiesto mezclaba nuevas y seguidas (borraba de más) → solo nuevas;
  `git checkout` revierte las seguidas. Rollback exige manifiesto (falla sin él).
- U20e `tar -d` no portable (BSD/GNU) → comparación byte a byte con `cmp` y
  re-ejecución idempotente (tar --diff no usado).
- U20f SHA fijo dentro del script se desincroniza del tar → `SENDASHA`
  obligatorio por entorno; el bloque de despliegue lo fija.
- Verificado en sandbox: ruta feliz, idempotencia, aborto con tar ajeno,
  rollback completo (.env, seguidas, añadidas). Fixture retirada.

## SHA vigente d8931ae5 (sustituye a 11c7e858: AppleDouble U28)

- El SHA 448cedfd correspondía al paquete sin los scripts finales. Al añadir
  `ops/proxy/prepare-senda.sh` (con comando exacto de rollback impreso) y
  `rollback-senda.sh` ya corregidos, el contenido cambió y el SHA pasó a
  `d8931ae577803c59753bfe6dc305f13da7d8aa47f72183cc2b31565e1400ec96`
  (334 entradas, 0 prohibidas, scripts finales verificados dentro del tar).
- U31 lo sustituye: `1e98972e6d1f4fb0300d22500120b9f6baa9b8ecdcbf61ecc19b624acf4e15fe`
  (334 entradas, 0 prohibidas, 0 rechazos del filtro; solo cambian los 5
  archivos del fix serve + su spec). `entrega-senda/senda-prod.tar` ya es ese.

## Entrega del paquete (U21)

- U21 Copia de entrega en `entrega-senda/senda-prod.tar` (mismo SHA
  `d8931ae5…c96` verificado tras mover; copia suelta en `/Users/jhomc/`
  eliminada). Ruta a usar en la subida. Fixture de harness retirada.

## Secretos por fichero + Tailscale no efímero (verificado en harness)

- U22 `prepare-senda.sh` lee `~/senda-secretos/{hc_sync_token,csrf_secret,
  ts_authkey}` con validación de formato/longitud/prefijo, sin mostrar
  valores ni pedirlos a mano; reutiliza operativos (sin rotación);
  `BIENESTAR_*` coherente + allowlist por entorno. Reintentos seguros.
- U23 Nodo no efímero: clave reutilizable + `TS_AUTH_ONCE` + volumen de
  estado; verificar `tags: [tag:senda]` en `tailscale status --json` y grants
  en consola antes del corte. Harness: ruta feliz, idempotencia, aborto con
  tar ajeno, rollback completo. Fixture retirada.

## Paquete definitivo 9e7ef101 + bloque de preparación

- U24 Tar reconstruido con scripts finales (334 entradas, 0 prohibidas;
  SHA `d8931ae5…c96`); copia de entrega en `entrega-senda/senda-prod.tar`
  (mismo SHA verificado). Referencias viejas actualizadas.
- U25 Verificación de tag/grants en el corte (no ejecutable desde aquí):
  `docker exec magi_tailscale tailscale status --json` debe incluir
  `tag:senda`; grants en consola limitados a tus dispositivos.

## Carpeta de entrega (U26, sin valores mostrados)

- U26 `entrega-senda/` contiene `senda-prod.tar` (SHA d8931ae5…c96
  verificado tras mover) + `hc_sync_token` (64B) + `csrf_secret` (97B),
  ambos 600 e idénticos a los operativos. Clave Tailscale: reutilizable o
  efímera a tu criterio (nodo no efímero por estado + `TS_AUTH_ONCE`);
  verificar tag `senda` y grants en consola antes de desplegar.

## Filtro corregido + SHA 11c7e858 (U27)

- U27 El aborto «rutas no previstas» lo causaban los 2 scripts (`prepare` y
  `rollback`), añadidos al tar sin añadirlos a la lista permitida. Lista
  corregida con rutas exactas (sin ampliar). Filtro probado contra el tar
  real: 0 rechazos. Tar reconstruido (scripts finales dentro, verificado por
  extracción) → SHA `d8931ae5…c96`, 334 entradas, 0 prohibidas.
  Referencias actualizadas en tasks y runbook.

## AppleDouble eliminados (U28, verificado en el fichero final)

- U28 El paquete contenía 29 `._*` en la VM (bsdtar macOS los genera por
  xattrs aunque `tar -tf` local no los mostraba). Reconstruido con
  `COPYFILE_DISABLE=1` + exclusión explícita `._*`.
- Verificado sobre el mismo tar final con 3 lectores: bsdtar (0 `._*`),
  filtro real extraído de `prepare-senda.sh` (0 rechazos en 334) y módulo
  `tarfile` de Python (334 miembros, 0 AppleDouble, sin pax headers).
- SHA `d8931ae5…c96`. Sustituir únicamente el archivo en la VM; secretos,
  respaldos y servicios intactos.

## Corte 2026-10-06 en curso (U30, ventana con móvil/HC pausados)

- U30 Respaldo nuevo tras parada (`AEGEN/apps/entrenamiento/data/`):
  `backup-pre-corte-20261006-mac.db`, SHA
  `ea5f4c75c5c2185e63f630ee324ce2cdf851203ab006759da4926f1b190e13e6`
  (integrity ok, esquema 24). training_sets 1513 (+12 sync desde el
  respaldo 20261005), resto igual. Equivalencia viva-vs-respaldo 16/16
  (conteo+hash). Copia externa en `respaldos-senda/20261006/` (SHA
  idéntico + `LEEME.txt`). Escritor Mac detenido (8000 libre); Mac queda
  detenido. Paquete `d8931ae5…c96` vigente.
- Pendiente (dueño en VM): subir tar + `backup-20261006` por medio privado,
  `prepare-senda.sh`, arrancar solo `senda`+`tailscale`, serve, HTTPS
  privado, equivalencia en destino, persistencia y recuperación; APK a la
  URL definitiva; validación conjunta lectura/escritura/undo/HC.
- Si pasa: GCP escritor canónico; Telegram e integración conversacional
  quedan pendientes; no se declara fusión completa. Rollback y ajenos
  intactos. Sin commits/push/merges ni recursos de pago.

## Dashboard por Tailscale serve (U31, corrige el 403 presentado como listo)

- Causa: el gate no fallaba. `tailscale serve` re-origina desde 127.0.0.1
  (netns compartido) y uvicorn sin `--proxy-headers` publica el peer real:
  el serve pasa como loopback. El 403 con peer 100.x era acceso directo a
  `http://<ip-tail>:8000/` (uvicorn escucha 0.0.0.0 en el netns): remoto por
  diseño, solo API con token. No se confía en `100.64.0.0/10` ni en XFF.
- Hallazgo previo al ensayo: tras el proxy el navegador usa `https://` pero
  uvicorn ve `http`, así que `_same_origin` rechazaría toda mutación servida.
  Fix: `GYM_BEHIND_TLS_PROXY=1` (configuración, solo compose de senda) fija
  el scheme efectivo a `https` para el check; sin el flag falla cerrado.
  Tokens, exenciones, rate-limit y gate intactos.
- Cambios: `src/security.py` (`tls_proxy_enabled`, `effective_scheme`),
  docstring de `src/network_access.py`, `GYM_BEHIND_TLS_PROXY=1` en
  `ops/proxy/compose-senda.yml`, §2.7 en `security-model.md`, doctrina
  corregida arriba. Suite sin e2e: 969 passed (7 tests nuevos); ruff/mypy
  limpios. Tar reconstruido (SHA `1e98972e…f4e15fe`, 334 entradas, 0
  prohibidas, filtro 0 rechazos, solo los 5 archivos previstos cambiaron);
  solo se reconstruye `senda`, volumen preservado, tailscale recreado tras
  senda; AEGEN intacto.

## U32: U31 atribuyó mal el 403; el peer 100.x venía del serve vía XFF (U32)

- Retractación: U31 afirmó que el serve llega como loopback y que el 403 con
  peer 100.x era acceso directo a `:8000`. Falso: el curl a la URL HTTPS
  devolvió 403 y registró la IP tailnet del Mac. El recorrido HTTPS genuino
  también presentaba peer 100.x.
- Mecanismo verificado en uvicorn 0.52.1 instalado
  (`middleware/proxy_headers.py`): con `--proxy-headers` y peer loopback de
  confianza (default `127.0.0.1`), uvicorn reescribe `scope['client']` desde
  `X-Forwarded-For`, que el reverse proxy de Tailscale rellena con la IP del
  cliente (`get_trusted_client_address` recorre de derecha a izquierda y
  devuelve el primer no-confiable: la IP tailnet). El repo nunca pasó ese
  flag (`start_server.sh`); si el contenedor vigente lo lleva, esa es la
  divergencia — pero no se afirma sin el `ps` vivo: el bloque de despliegue
  lo comprueba primero y aborta si no hay flag (re-derivar) o si la versión
  instalada difiere de 0.52.1 (uv.lock). Test nuevo con el middleware real
  reproduce el log observado (`client=('100.64.1.2', 0)` en el gate).
- Fix ajustado: `--no-proxy-headers` EXPLÍCITO en senda (no basta omitir el
  flag; `Config(proxy_headers=False)` verificado en la 0.52.1 instalada);
  sin el middleware el serve vuelve a verse como 127.0.0.1 y el XFF se
  ignora. Se conserva `GYM_BEHIND_TLS_PROXY=1` (scheme https para Origin; Go
  ReverseProxy no fija `X-Forwarded-Proto`). Gate, tokens, puertos y funnel
  intactos. Rate-limit: VERIFICADO, no intacto — el gate exime a loopback
  antes de limitar, así que el tráfico servido (API incluida) no tiene
  límite por peer; el limitador cubre solo peers no-loopback (bridge AEGEN,
  tailnet directa). Test que lo fija + consecuencia en spec; sin rediseño
  (limitar loopback rompería healthcheck/dev).
- Despliegue mínimo (no el tar completo: incluye cambios AEGEN y pisaría la
  corrección local del Compose): parche `entrega-senda/senda-fix-u32.tar`
  (SHA `3901e685…0143db`) con solo `src/security.py`,
  `src/network_access.py`, `scripts/start_server.sh` (3 archivos; tests y
  docs quedan locales);
  `compose-senda.yml` (línea `GYM_BEHIND_TLS_PROXY=1`) por edición manual
  con `config --quiet` después. Rebuild solo `senda`, `--no-deps`, ambos
  volúmenes preservados, tailscale recreado tras senda, rollback de código
  (copias previas + compose respaldado) e imagen (etiqueta recuperable sobre
  el ID vigente; reconstruir NO equivale a restaurar).
- Suite sin e2e: 971 passed (9 tests nuevos); ruff/mypy limpios.
- Acceso web NO declarado resuelto: pendiente lectura + escritura reversible
  por la URL HTTPS real desde el Mac.

## U33: lentitud de SENDA (cuello demostrado, corregido, verificado)

- Evidencia: GET / interno 2,422/1,078/1,010 s con 525,452 bytes; por HTTPS
  4,652/1,958 s. Reproducido en Mac con copia de la DB viva (mismo SHA
  `6e3ff694…ae1c`): 523,666 bytes en 0.740/0.515/0.532 s.
- Localización (mismos datos): build_metrics_index 0.149 s (17 capas, 4
  releídas por recovery), chart_pfr_timeline 0.201 s (baselines ×2 +
  aggregate_sets ×2: hover y RIR), chart_metrics_index 0.113 s.
  525 KB = figura métricas 345 KB (x 97 + y 54 + customdata 192 KB: 13
  trazas × 533 pts con etiquetas por punto para toggles instantáneos y
  pan/zoom, por diseño) + sistémica 26 KB + ~152 KB plantilla. Navegadores
  reciben gzip (~70 KB en red); el coste dominante es cómputo servidor.
- Fix (mismo contenido, cero SQL duplicado, sin infra nueva): F1 capas de
  salud una vez y compartidas con recovery (`layers=`); F2 baselines 4→1 y
  una sola agregación hover+RIR por recorrido (`baselines=`/`totals=`,
  opcionales); F3 vectorización de applies por fila; F4 `y` de métricas a
  2 decimales (subpíxel, tooltip intacto en customdata).
- Equivalencia probada en datos reales: recovery/aggregate/calculate/_pfr_df
  day+week bit-idénticos con y sin params; redondeo acotado a 0.005000.
  Suite sin e2e: 971 passed; ruff/mypy limpios.
- Antes/después (Mac, misma DB): GET / 0.740/0.515/0.532 → 0.608/0.413/0.462 s
  (-18%/-20%/-13%); bytes 523,666 → 511,951 (-2.2%); métricas JSON 344,785 →
  333,070 (-3.4%); pfr 0.201 → 0.137 s (-32%); índice 0.149 → 0.120 s (-19%).
- Despliegue solo SENDA (parche `entrega-senda/senda-perf-u33.tar`, SHA
  `35e7b5d2…21db`, solo 10 src afectados; volumen preservado; rollback de
  código+imagen; AEGEN intacto). Navegación real en navegador y móvil:
  pendiente del dueño.

## U33b: coste por vista + arranque en frío (sin cambios de código)

- Servidor en Mac, mismos datos (SHA `6e3ff694…ae1c`): `/` 0.413 s/511,951 B;
  `/diario` 0.026 s/225,861 B; `/fecha/editor` 0.006 s/102 KB;
  `/alimentacion/editor` 0.008 s/56 KB; `/diario/navigator` 0.003 s/12 KB;
  `/sugerencia/banner` 0.002 s/vacío. El dashboard es la única vista cara
  en servidor; cambio de día y alimentación cuestan transferencia+cliente.
- Arranque en frío medido: imports 0.748 s + primer GET 0.662 s vs 0.422 s
  en caliente (extra ~0.24 s Mac: Jinja + páginas DB frías + cachés).
- Hipótesis 4.665 s (ABIERTAS hasta verificar en GCP; lo local no concluye
  allí): (1) primera petición tras (re)arranque en frío — apoyado en local
  (imports 0.748 s + extra primer hit 0.24 s Mac) pero pendiente de
  timestamps arranque-vs-petición en GCP; (2) solape con sync — magnitud
  pequeña en local aislado (lote 400 ops = 5 ms) SIN descartar contención en
  GCP (disco más lento, lotes mayores, peticiones solapadas); (3) bloqueos
  SQLite — WAL activo en local SIN descartar stalls de checkpoint/locks en
  GCP; (4) CDN — 130 ms en banda ancha local; impacto en datos móviles
  demostrado por emulación (plotly 1.8 s en 3G).
- Plotly se carga de CDN en runtime (jsdelivr, SRI): en móvil suma DNS+TLS+
  descarga antes del primer render; no se propone vendorizar (rompería el
  budget first-party) sin medir antes en DevTools.
- Reales post-U33 (dueño, URL vigente https://senda.tail402592.ts.net/):
  GCP interno 4.665/0.905/0.817 s, documento 513,709 B; Mac HTTPS TTFB
  2.086/1.169/1.447 s y total 2.710/1.751/1.987 s (todo 200). El primer
  GCP (4.665 s) alimenta la hipótesis de frío; los tibios confirman la
  mejora parcial de U33.
- Navegador medido por el agente (Chromium local, mismos datos, servidor
  tibio; throttle 4x verificado 19→71 ms): `/` escritorio 469 TTFB + 877
  cliente = 1,346 ms (512 KB); móvil CPU4x 523 + 843 = 1,366 ms; móvil
  CPU4x+3G 513 + 3,576 = 4,089 ms (plotly CDN 1.8 s, documento ~1.7 s).
  Cambio de día settle real 110 ms escritorio / 295 ms móvil (fragmentos
  4–24 ms); `/diario` 106/275 ms. Demora visible = solo la carga inicial:
  en banda ancha ~40 % servidor + ~60 % cliente (parse+CDN+react; el render
  NO escala con CPU: throttle 4x ≈ igual); en datos móviles domina la
  transferencia (849 KB totales).
- Decisión: NO procede otro parche. Todo lo que queda toca
  diseño/producto/presupuesto (recortar payload = contrato JS o menos datos;
  vendorizar plotly = rompe budget first-party; más cómputo = reescritura
  estructural de analysis_data) o exige medidas del entorno afectado.
  Mejora declarada solo la verificada; navegación real en dispositivo del
  dueño pendiente (abrir pantalla / describir lentitud).

## U33d: evaluación sin código (gzip, nulos, CDN; local, no concluyente en GCP)

- gzip (Starlette 1.4.1, `compresslevel` tunable, cuerpos >128 KB van a
  threadpool: NO bloquea el loop): página real 511,951 B → nivel 9: 34,184 B
  en 10.1 ms; nivel 6: 36,248 B (+6 %) en 4.1 ms; nivel 4: 57,529 B (+68 %).
  Rechazado: −6 ms de CPU fuera del loop no mueven TTFB; +2 KB en red.
- Nulos de la figura métricas: 5,693/6,929 puntos (82 %) con coste ≈75 % de
  sus 333 KB (x + `null` + customdata con "—" por punto). Quitarlos deja
  segmentos idénticos (`connectgaps` une los mismos puntos reales) pero
  cambia límites de pan: OPCIÓN de producto (decisión requerida),
  impacto MEDIDO en local: figura −81 % crudo, gzip 17,033→10,171 B (−40 %),
  página gzip ≈ −20 % (≈−7 KB). NO implementado unilateralmente.
- Etiquetas customdata: dedup MEDIDO −18 KB crudo pero solo −2.9 KB gzip
  (−8.6 % página) con churn de contrato JS: ratio pobre, aparcado.
- Serialización (separadores/UTF-8): MEDIDO ~0 % en red (plotly ya compacta;
  gzip absorbe la repetición Unicode). Rechazado con evidencia.
- Vendorizar plotly: file medido 340,732 B transfer (fresco); first-party JS
  actual 288 KB en disco (sumaría ~1 MB: exige commit de presupuesto).
  Ahorro de tiempo solo en red lenta/dispositivo real: PENDIENTE remoto
  (no presentar la emulación 3G como resultado).
- Reescritura `analysis_data` en un solo escaneo: SIN MEDIR (proyección
  retirada: no se presenta como resultado).
- Corrección: U33b/U33c son evidencia LOCAL (simulación/emulación); las
  cifras remotas que valen son las del dueño (GCP/Mac/dispositivo).
  Render-CPU: en emulación no escala con throttle; confirmación en
  dispositivo real pendiente.

## U33e: tiempo hasta utilizable + gzip remoto (investigación, sin código)

- REMOTO (dueño): HTTP 200, gzip activo, 513,709 → 34,275 B (predicción
  local 34,184 B: la compresión efectiva funciona; no es el problema).
- Utilizable = hover con tooltip propio + toggle de chip sin red, medido
  por el agente en Chromium local (servidor tibio, mismos datos; throttle
  4x verificado): escritorio TTFB 495 ms → svg 1,377 → hover 1,466 ms
  (tooltip real 66 cars) → toggle chip 36 ms, 0 peticiones tras la carga;
  móvil CPU4x 557 → 1,327 → 1,496 ms, toggle 76 ms (drawer móvil abierto
  como un usuario: el catálogo es drawer colapsado ≤1023 px por diseño;
  toggle 2x por CPU pero <0.1 s). U33c queda superado por esta metodología
  (solo retenido su bound 3G: transferencia domina en datos lentos).
- Descomposición visible (banda ancha): servidor ~35-40 % + cliente ~60-65 %
  (parse 512 KB + CDN plotly + react + bind); móvil con CPU lenta NO empeora
  (throttle-verificado) → el cliente no está limitado por CPU sino por
  transferencia+parse. Día/diario/comida ya medidos sub-300 ms.
- Veredicto: sin parche unilateral más allá de U33. Lo único con impacto
  real (poda de nulos, −40 % figura gzip) cambia bounds de pan → decisión
  de producto pendiente. Todo lo demás, rechazado/aparcado con medida.
- Nombre senda ya aplicado (tailnet + URL vigente); compose local aún con
  `--hostname=senda-gcp`: alinear solo en copia local del dueño, nunca por
  tar (regla U32).
- Comprobaciones GCP pendientes (comandos entregados): compresión efectiva
  (identity vs gzip), bytes transferidos y carga inicial real con contexto
  de arranque (frío vs tibio).
- REMOTO CONFIRMADO (dueño): HTTP 200, gzip activo, 513,709 → 34,275 bytes
  en red (predicción local 34,184 B: desviación 0.3 %, solo crecimiento de
  datos). La compresión efectiva NO es el problema.
