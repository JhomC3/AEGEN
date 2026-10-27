# Procedimiento de transferencia y rollback (PROPUESTA, no ejecutada)

Requiere autorización operativa explícita. Sin ella, el destino canónico es
solo implementación local pendiente de transferencia (RF-10/RF-11 pendientes).

## Precondiciones (todas superadas antes del corte)

- Destino verificado: app en `apps/entrenamiento/` arranca, suite sin e2e 962 passed,
  subagente Senda con consultas/escrituras probadas (21 tests), Rumbo reconciliado a `e9ee8ab`.
- Origen verificado en `e9ee8ab` (limpio salvo conversación ajena sin seguimiento;
  worktrees `feat/rumbo@529e84d`, `feat/movil-legible@e9ee8ab` intactos y ajenos).
- Android-fuente incorporado en `apps/entrenamiento/android/` (solo fuente:
  `app/src`, `gradle/`, `*.kts`, `gradlew`; SDK/build/caches excluidos).
  El build lee `../data/hc_sync_token`: en destino operativo `data/` vive junto
  a `apps/` igual que en origen, sin cambios.
- Ensayo de recuperación EJECUTADO Y SUPERADO el 2026-10-04 en copias
  aisladas (`.tmp-ensayo/`, retirado después): backup `.backup` WAL-seguro,
  escritura posterior (sesión 70 kg + respuesta ex01), restauración en destino
  y reconciliación re-aplicando por servicios; destino idéntico al origen
  (sets [(70.0,)], 37 respuestas). Sin este ensayo superado no hay corte.
- Conexión del subagente: `BIENESTAR_DOMAIN_URL=http://127.0.0.1:8000`
  (loopback del servidor del dominio en el mismo host),
  `BIENESTAR_SYNC_TOKEN` = token operativo, chats autorizados configurados.
  El puerto LAN del dominio sigue reservado al móvil y al sync.

## Transferencia (un solo escritor canónico)

1. Ventana sin escrituras: detener el proceso de origen **antes** del backup
   (las escrituras en vuelo fallan rápido; el móvil conserva `pending_writes`
   según B4 y las reintentará). Comprobar puerto 8000 libre y que ningún
   proceso escribe la DB (`lsof` o fuser).
2. Backup consistente ya sin escritores: `sqlite3 data/lifestyle.db ".backup
   main backup-pre-corte.db"` (WAL seguro; nunca `cp` en vivo) + copia de
   `data/backups/` recientes. Registrar SHA-256 y conteos por tabla.
3. Reconciliación final: comparar conteos del backup contra el origen detenido
   (iguales por construcción); cualquier diferencia aborta el corte.
4. Copiar backup + `hc_sync_token` + `csrf_secret` al destino operativo
   (mismo token = Android sigue funcionando sin rebuild).
5. `init_db` en destino (migraciones idempotentes; backup previo automático);
   verificar conteos idénticos y `undo peek` coherente.
6. Arrancar destino con `start_server.sh` desde `apps/entrenamiento/`;
   probar `/healthz`, 1 lectura y 1 escritura+undo por API con DB operativa.
7. Declarar destino escritor canónico; el checkout origen queda solo lectura
   (no se borra: historia y worktrees ajenos intactos).

## Rollback y límites

- Copia externa del respaldo 2026-10-05: `/Users/jhomc/Proyectos/respaldos-senda/20261005/`
  (`backup-pre-corte-20261005-mac.db`, SHA-256 completo
  `15d1c51740cdffb5b93592b8486018d480a07c31eda91f0e610e791f80a74376`,
  + `LEEME.txt` con esquema/conteos). Fuera del paquete de despliegue.
  Paquete: `AEGEN/.tmp-gcp/senda-prod.tar`, SHA-256 completo
  `f4c11fedfab6834c945a3000b692bd23bd3f0b0f6b2152acfd679d7bc3f9c3df`.
- Rollback sin API accesible: con ambos parados, comparar conteos/hashes del
  destino contra el respaldo; si hay escrituras posteriores, identificarlas
  por fecha/tabla y re-aplicarlas tras restaurar (nunca backup antiguo
  encima); rearrancar el origen con su DB intacta y verificar `/healthz` +
  lecturas; solo entonces declarar el origen escritor de nuevo.
- Comandos concretos (origen Mac; en GCP con sus rutas):
  `curl --max-time 5 .../healthz` (debe fallar) y `pgrep -f uvicorn` vacío
  confirman parada; `.backup` WAL-seguro + `PRAGMA integrity_check` +
  `SELECT MAX(version)` + conteos/hashes por tabla comparan; restaurar =
  copiar respaldo a DB limpia + re-aplicar posteriores por API/servicios +
  igualdad total + `undo peek` coherente + una escritura+undo de prueba.
- Ensayo U24 superado en aislado (altas, modificación, borrado, Rumbo):
  detección por tablas/journal, reconciliación exacta (timestamps de
  auditoría excluidos con justificación), undo funcional tras recuperar,
  backup y DB viva intactos (SHA verificados antes/después).
- SENDA detenido desde el reinicio del entorno y mantenido así durante la
  preparación: **fuera de servicio** hasta el corte (puerto 8000 libre,
  verificado; sin autostart: proceso manual en segundo plano, no persiste
  reinicios).

- Si hay escrituras posteriores al backup: reconciliar vía API (releer días
  afectados y re-aplicar), nunca restaurar el backup antiguo encima.
- Si no hay escrituras posteriores: detener destino, restaurar backup,
  rearrancar origen, verificar conteos.
- Secretos y URLs vuelven a su ruta origen; Android no requiere cambios si el
  token y el host LAN se conservan (mismo `applicationId`, mismos IDs).
- No probado contra dispositivo real ni red del teléfono (pendiente T8b).
- Renombre aplicado: SENDA (marca visible + subagente `senda_specialist`,
  comando `/senda` con alias `/bienestar`); rutas API, DB, credenciales e IDs
  persistentes intactos.

## Corte ejecutado 2026-10-04 13:03 (pendiente validación móvil)

- Origen detenido ordenadamente (SIGTERM, puerto 8000 libre; servidor de
  `feat/movil-legible:51329` ajeno intacto).
- Backup `.backup` WAL-seguro: `backup-pre-corte-20261004-130323.db`,
  SHA-256 `18db4659…4993bc`, integrity ok, esquema 24, conteos
  (training_sets 1501, diario 3087, breathing 21, rumbo_dia 0,
  rumbo_respuestas 36, undo 10, ejercicios 29, alimentos 67).
- Transferidos DB + `hc_sync_token` + `csrf_secret` (mismo token: Android sin
  cambios), modo 600, ignorados por git (`apps/entrenamiento/data/`).
- Destino arrancado con `start_server.sh` (secretos reutilizados, sin
  regenerar): `/healthz` 200, lecturas reales, escritura controlada
  2001-01-02 + undo verificados sin residuo (cima restaurada a #390).
- SENDA contra operativo: consultas reales OK (sesión/diario/rumbo).
  `.env`: `BIENESTAR_DOMAIN_URL` + `BIENESTAR_SYNC_TOKEN` configurados
  (ignorado por git); allowlist pendiente del chat id del dueño.
- Origen detenido y disponible para rollback; NO declarado canónico hasta
  validación móvil.

## Equivalencia backup-destino verificada (pre-pruebas externas)

16 tablas comparadas por contenido (conteo + hash): 15/16 idénticas
(training_sets 1501, diario 3087, parámetros 215, breathing 21, splits/items,
ejercicios 29, plantillas 4/40, alimentos 67, rumbo 0/0/36, sync_reports 5).
`undo_entries`: 10 → 9 por el tope de la pila (máx 10): el ciclo de prueba
controlada añadió la #391 y al consumirla podó la más antigua (#381, por
diseño); la cima #390 (sesión 2026-10-05) intacta. Sin residuos de pruebas
(día 2001-01-02 vacío verificado).

## Pérdida registrada: entrada de undo #381 (2026-10-04)

- Qué era: `kind=sesion`, creada 2026-09-28, permitía deshacer el guardado de
  la sesión del 2026-09-29 (restaurarla a vacía). No se restaura la DB ni se
  reinserta la entrada.
- Datos de usuario intactos: 12 series del 2026-09-29 idénticas en backup y
  destino. Solo se perdió la capacidad de deshacer esa acción de hace 6 días.
- Causa: tope de la pila (máx 10) activado por el ciclo de prueba controlada
  previo al corte.
- Regla desde ahora: antes de cualquier prueba que toque el journal operativo,
  comprobar capacidad (`undo/peek` + tamaño); si el push puede podar historia
  real, validar ese recorrido en DB aislada, nunca en la operativa.
