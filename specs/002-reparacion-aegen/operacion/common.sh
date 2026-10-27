#!/usr/bin/env bash
# Solo se carga desde los comandos de esta entrega.
set -Eeuo pipefail
umask 077
ROOT="$HOME/AEGEN"
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
RUN=$(dirname "$HERE")
BACKUP="$RUN/respaldo"
cd "$ROOT"
dc() {
  docker-compose --project-directory "$ROOT" --env-file "$ROOT/.env" \
    -f "$ROOT/docker-compose.yml" -f "$1" -p aegen "${@:2}"
}
verify_bundle() { (cd "$RUN" && sha256sum -c manifest.sha256 >/dev/null); }
verify_backup() { (cd "$BACKUP" && sha256sum -c manifest.sha256 >/dev/null); }
image_id() { docker inspect -f '{{.Image}}' "$1"; }
check_others() {
  docker inspect -f '{{.Id}} {{.Image}} {{.State.StartedAt}}' \
    magi_redis magi_tailscale > "$RUN/ajenos.actual"
  cmp "$BACKUP/ajenos.txt" "$RUN/ajenos.actual"
}
wait_app() {
  local n
  for n in $(seq 1 90); do
    if [ "$(docker inspect -f '{{.State.Health.Status}}' magi_app_prod)" = healthy ]; then
      return 0
    fi
    sleep 2
  done
  echo 'AEGEN no confirmó salud Docker; consultar rollback.' >&2
  return 1
}
verify_env() {
  test "$(sha256sum "$ROOT/.env" | cut -d' ' -f1)" = "$(cat "$BACKUP/env.sha256")"
  test "$(stat -c '%a:%u:%g' "$ROOT/.env")" = "$(cat "$BACKUP/env.permisos")"
  cmp "$ROOT/docker-compose.yml" "$BACKUP/docker-compose.yml"
}
verify_runtime() {
  local container=$1 image=$2
  docker run --rm --network none --read-only \
    -e PYTHONDONTWRITEBYTECODE=1 --entrypoint python \
    -v "$RUN:/repair:ro" "$image" \
    /repair/operacion/verificar_base.py "$container"
}
