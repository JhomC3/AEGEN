#!/usr/bin/env bash
# Preparación en la VM. No detiene ni recrea contenedores de servicio.
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
verify_bundle
test ! -e "$RUN/PREPARADO" || { echo 'Esta entrega ya está preparada.'; exit 0; }
test ! -e "$BACKUP" || { echo 'Intento incompleto: conservar y revisar esta carpeta.'; exit 1; }
test ! -e "$RUN/activar.yml"
test "$(git rev-parse HEAD)" = 11487668e1a8435cdc6f99b84dbfef2db211fe50
test -f .env
test -d storage
test "$(stat -c '%a:%u:%g' .env)" = '640:1000:10001' || {
  echo 'Permisos .env distintos del inventario: no se han modificado.'; exit 1;
}
for container in magi_app_prod magi_polling magi_redis magi_tailscale; do
  test "$(docker inspect -f '{{.State.Health.Status}}' "$container")" = healthy
done
mkdir -m 700 "$BACKUP"
git status --short > "$BACKUP/git-status.txt"
git diff --binary > "$BACKUP/tracked.diff"
git rev-parse HEAD > "$BACKUP/HEAD.txt"
sha256sum .env | cut -d' ' -f1 > "$BACKUP/env.sha256"
stat -c '%a:%u:%g' .env > "$BACKUP/env.permisos"
cp -p docker-compose.yml "$BACKUP/docker-compose.yml"
# No guardar .env ni listar su contenido: la configuración no cambia.
docker inspect -f '{{.Id}} {{.Image}} {{.State.StartedAt}}' \
  magi_redis magi_tailscale > "$BACKUP/ajenos.txt"
APP_OLD=$(image_id magi_app_prod)
POLL_OLD=$(image_id magi_polling)
verify_runtime app "$APP_OLD"
verify_runtime polling "$POLL_OLD"
printf '%s\n' "$APP_OLD" > "$BACKUP/app.id"
printf '%s\n' "$POLL_OLD" > "$BACKUP/polling.id"
STAMP=$(basename "$RUN")
APP_TAG="aegen-rollback/app:$STAMP"
POLL_TAG="aegen-rollback/polling:$STAMP"
APP_BYTES=$(docker image inspect -f '{{.Size}}' "$APP_OLD")
POLL_BYTES=$(docker image inspect -f '{{.Size}}' "$POLL_OLD")
FREE_KB=$(df -Pk "$ROOT" | awk 'END {print $4}')
STORAGE_KB=$(du -sk "$ROOT/storage" | awk '{print $1}')
# Cota conservadora para dos exports, imágenes nuevas y margen de 1 GiB.
NEED_KB=$(( (2 * (APP_BYTES + POLL_BYTES)) / 1024 + 2 * STORAGE_KB + 1048576 ))
test "$FREE_KB" -ge "$NEED_KB" || {
  echo "Espacio insuficiente: disponibles=${FREE_KB}KiB necesarios=${NEED_KB}KiB"; exit 1;
}
docker tag "$APP_OLD" "$APP_TAG"
docker tag "$POLL_OLD" "$POLL_TAG"
docker save "$APP_TAG" "$POLL_TAG" | gzip > "$BACKUP/imagenes.tar.gz"
gzip -t "$BACKUP/imagenes.tar.gz"
cat > "$BACKUP/rollback.yml" <<EOF
services:
  app:
    image: $APP_OLD
  polling:
    image: $POLL_OLD
EOF
dc "$BACKUP/rollback.yml" config --quiet
(
  cd "$BACKUP"
  sha256sum HEAD.txt git-status.txt tracked.diff env.sha256 env.permisos \
    docker-compose.yml ajenos.txt app.id polling.id imagenes.tar.gz rollback.yml > manifest.sha256
)
verify_backup
# Dockerfile solo superpone la reparación a cada imagen que ya existe.
docker build --network none --pull=false --build-arg "BASE_IMAGE=$APP_TAG" \
  -t "aegen-repair002/app:$STAMP" "$RUN"
docker build --network none --pull=false --build-arg "BASE_IMAGE=$POLL_TAG" \
  -t "aegen-repair002/polling:$STAMP" "$RUN"
APP_NEW=$(docker image inspect -f '{{.Id}}' "aegen-repair002/app:$STAMP")
POLL_NEW=$(docker image inspect -f '{{.Id}}' "aegen-repair002/polling:$STAMP")
cat > "$RUN/activar.yml" <<EOF
services:
  app:
    image: $APP_NEW
  polling:
    image: $POLL_NEW
EOF
dc "$RUN/activar.yml" config --quiet
verify_env
check_others
test "$(image_id magi_app_prod)" = "$APP_OLD"
test "$(image_id magi_polling)" = "$POLL_OLD"
git status --short > "$RUN/git-status.final"
cmp "$BACKUP/git-status.txt" "$RUN/git-status.final"
printf '%s\n' "$APP_NEW" > "$RUN/app.nueva.id"
printf '%s\n' "$POLL_NEW" > "$RUN/polling.nueva.id"
(cd "$RUN" && sha256sum activar.yml app.nueva.id polling.nueva.id > preparado.sha256)
printf '%s\n' "$RUN" > "$RUN/PREPARADO"
printf 'PREPARADO. Ningún servicio reiniciado.\nACTIVAR (requiere autorización): bash %q\nROLLBACK: bash %q\n' \
  "$HERE/activar.sh" "$HERE/rollback.sh"
