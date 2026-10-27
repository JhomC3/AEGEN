#!/usr/bin/env bash
# Restaura imágenes exactas, conservando configuración y datos actuales.
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
verify_backup
verify_env
check_others
docker load < "$BACKUP/imagenes.tar.gz"
docker image inspect "$(cat "$BACKUP/app.id")" >/dev/null
docker image inspect "$(cat "$BACKUP/polling.id")" >/dev/null
dc "$BACKUP/rollback.yml" config --quiet
dc "$BACKUP/rollback.yml" stop polling
dc "$BACKUP/rollback.yml" stop app
dc "$BACKUP/rollback.yml" up -d --no-deps --no-build --pull never app
wait_app
dc "$BACKUP/rollback.yml" up -d --no-deps --no-build --pull never polling
test "$(image_id magi_app_prod)" = "$(cat "$BACKUP/app.id")"
test "$(image_id magi_polling)" = "$(cat "$BACKUP/polling.id")"
check_others
verify_env
echo 'ROLLBACK DE IMÁGENES VERIFICADO. Datos y checkout preservados.'
