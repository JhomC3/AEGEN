#!/usr/bin/env bash
# Ejecutar únicamente después de autorizar la interrupción de AEGEN.
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
verify_bundle
verify_backup
test -f "$RUN/PREPARADO"
(cd "$RUN" && sha256sum -c preparado.sha256 >/dev/null)
test ! -e "$RUN/ACTIVADO"
verify_env
check_others
test "$(image_id magi_app_prod)" = "$(cat "$BACKUP/app.id")"
test "$(image_id magi_polling)" = "$(cat "$BACKUP/polling.id")"
dc "$RUN/activar.yml" config --quiet
FREE_KB=$(df -Pk "$ROOT" | awk 'END {print $4}')
STORAGE_KB=$(du -sk "$ROOT/storage" | awk '{print $1}')
test "$FREE_KB" -ge "$((2 * STORAGE_KB + 1048576))" || {
  echo 'No hay margen para el respaldo de storage; no se detuvo nada.'; exit 1;
}
trap 'echo "ACTIVACIÓN INTERRUMPIDA. Rollback: bash $HERE/rollback.sh" >&2' ERR
# Polling se para antes de cambiar app: nunca hay dos pollers ni app en vuelo.
dc "$RUN/activar.yml" stop polling
dc "$RUN/activar.yml" stop app
# Copia coherente de storage, incluido WAL, con ambos escritores detenidos.
tar -czf "$BACKUP/storage-pre-activacion.tar.gz" -C "$ROOT" storage
gzip -t "$BACKUP/storage-pre-activacion.tar.gz"
(cd "$BACKUP" && sha256sum storage-pre-activacion.tar.gz > storage.sha256)
dc "$RUN/activar.yml" up -d --no-deps --no-build --pull never app
wait_app
test "$(image_id magi_app_prod)" = "$(cat "$RUN/app.nueva.id")"
dc "$RUN/activar.yml" up -d --no-deps --no-build --pull never polling
test "$(image_id magi_polling)" = "$(cat "$RUN/polling.nueva.id")"
check_others
verify_env
date -u +%FT%TZ > "$RUN/ACTIVADO"
echo 'ACTIVADO. Falta validar proveedor y Telegram; no se declara reparado.'
