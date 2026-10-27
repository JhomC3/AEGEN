#!/bin/bash
# Preparación del despliegue SENDA en GCP — NO arranca nada operativo.
# Aborta ante cualquier fallo (set -euo pipefail). Usa siempre ambos
# Compose (-f ×2) y proyecto explícito (-p aegen).
# No toca app/polling/redis en ejecución ni crea contenedores.
set -euo pipefail

AEGEN_DIR="${AEGEN_DIR:-$HOME/AEGEN}"
COMPOSE="docker-compose -f docker-compose.yml -f ops/proxy/compose-senda.yml -p aegen"
TAR="${SENDATAR:-$HOME/senda-prod.tar}"
# SHA del paquete, obligatorio por entorno (lo indica el bloque de despliegue;
# sin valor fijo dentro del script para no desincronizarse del tar vigente).
SHA="${SENDASHA:?falta SENDASHA: verificar el SHA publicado antes de ejecutar}"

cd "$AEGEN_DIR"
git rev-parse --is-inside-work-tree >/dev/null
[ -f docker-compose.yml ] || { echo "ERROR: no es el checkout AEGEN"; exit 1; }

echo "== [1/7] paquete verificado ANTES de modificar archivos =="
[ -f "$TAR" ] || { echo "ERROR: falta $TAR"; exit 1; }
echo "$SHA  $TAR" | sha256sum -c -

echo "== [2/7] respaldo recuperable de lo existente =="
TS=$(date +%Y%m%d-%H%M%S)
BK="$HOME/.aegen-respaldo-$TS"
mkdir -p "$BK"
cp .env docker-compose.yml "$BK/"
docker images --format '{{.Repository}}:{{.Tag}} {{.ID}}' > "$BK/imagenes.txt"
docker-compose ps > "$BK/contenedores.txt"
echo "respaldo en $BK"

HAY_PREVIAS=0
for p in apps/entrenamiento ops/senda-test src/personality/skills/bienestar tests/unit/personality/test_bienestar_skill.py; do
  [ -e "$p" ] && HAY_PREVIAS=1
done
if [ "$HAY_PREVIAS" -eq 1 ]; then
  # Compara byte a byte lo archivado contra lo existente (portable sh+tar;
  # sin depender de `tar -d`, distinto entre BSD y GNU).
  DIFIERE=""
  AUSENTE=0
  while IFS= read -r f; do
    case "$f" in */) continue;; esac
    if [ ! -e "$f" ]; then AUSENTE=1; continue; fi
    if ! cmp -s <(tar -xOf "$TAR" "$f") "$f"; then
      echo "difiere del paquete: $f"
      DIFIERE=1
    fi
  done <<LISTA
$(tar -tf "$TAR")
LISTA
  if [ -n "$DIFIERE" ]; then
    echo "ERROR: existen rutas que difieren del paquete (trabajo ajeno o resto anterior)"
    echo "resolver a mano; nada se modificó en este paso"
    exit 1
  fi
  if [ "$AUSENTE" -eq 0 ]; then
    echo "rutas ya presentes e idénticas al paquete: se continúa sin extraer"
    SKIP_EXTRACT=1
  fi
fi
echo "== [3/7] extracción (solo rutas del paquete) =="
if tar -tf "$TAR" | grep -vE '^apps/entrenamiento/(app\.py|config\.py|src/|templates/|static/|scripts/|tests/|docs/|pyproject\.toml|uv\.lock|README\.md|sdd-lock\.json|Dockerfile|PROCEDENCIA\.md)|^ops/proxy/(compose-senda\.yml|Caddyfile|prepare-senda\.sh|rollback-senda\.sh)$|^ops/senda-test/docker-compose\.yml$|^src/personality/skills/bienestar/|^tests/unit/personality/test_bienestar_skill\.py$|^src/(agents/orchestrator/routing/(intent_parser|intent_patterns_data|specialist_mapper)\.py|core/(config/base|routing_models)\.py|tools/polling\.py)$|^\.env\.example$|^\.gitignore$' | grep -q .; then
  echo "ERROR: el tar contiene rutas no previstas" >&2
  exit 1
fi
if [ -z "${SKIP_EXTRACT:-}" ]; then
  tar -xf "$TAR"
fi
# Manifiesto SOLO con rutas nuevas (las modificadas seguidas se revierten
# con `git checkout`, nunca se borran).
{
  echo "apps/entrenamiento"
  echo "ops/senda-test"
  echo "ops/proxy/compose-senda.yml"
  echo "ops/proxy/Caddyfile"
  echo "src/personality/skills/bienestar"
  echo "tests/unit/personality/test_bienestar_skill.py"
} > "$BK/anadidos.txt"
git status --short | head -n 25

echo "== [4/7] secretos desde ficheros (operativos del Mac; sin mostrarlos) =="
touch .env && chmod 600 .env
# Fuente: transferencia privada previa a ~/senda-secretos/ (nunca el chat,
# nunca valores tecleados). Reutiliza los operativos: sin rotación.
SEC_DIR="${SECRETS_DIR:-$HOME/senda-secretos}"
leer_secreto() { # $1=nombre, $2=archivo; imprime valor, valida formato
  f="$SEC_DIR/$2"
  [ -f "$f" ] || { echo "ERROR: falta $f (transferencia privada previa)"; exit 1; }
  v=$(tr -d '\n\r ' < "$f")
  [ -n "$v" ] || { echo "ERROR: $f vacío"; exit 1; }
  printf '%s' "$v"
}
S1=$(leer_secreto SENDA_SYNC_TOKEN hc_sync_token)
case "$S1" in *[!0-9a-f]*|"") echo "ERROR: hc_sync_token sin formato hex" >&2; exit 1;; esac
[ "${#S1}" -eq 64 ] || { echo "ERROR: hc_sync_token longitud ${#S1}, esperada 64" >&2; exit 1; }
S2=$(leer_secreto SENDA_CSRF_SECRET csrf_secret)
case "$S2" in *[!0-9a-f]*|"") echo "ERROR: csrf_secret sin formato hex" >&2; exit 1;; esac
[ "${#S2}" -eq 96 ] || { echo "ERROR: csrf_secret longitud ${#S2}, esperada 96" >&2; exit 1; }
S3=$(leer_secreto TS_AUTHKEY ts_authkey)
case "$S3" in tskey-auth-*) ;; *) echo "ERROR: ts_authkey sin prefijo tskey-auth-" >&2; exit 1;; esac
gettok() { grep "^$1=" .env 2>/dev/null | cut -d= -f2- | head -n 1; return 0; }
E1=$(gettok SENDA_SYNC_TOKEN); [ -z "$E1" ] && printf 'SENDA_SYNC_TOKEN=%s\n' "$S1" >> .env
E2=$(gettok SENDA_CSRF_SECRET); [ -z "$E2" ] && printf 'SENDA_CSRF_SECRET=%s\n' "$S2" >> .env
E3=$(gettok TS_AUTHKEY); [ -z "$E3" ] && printf 'TS_AUTHKEY=%s\n' "$S3" >> .env
E3=$(gettok BIENESTAR_SYNC_TOKEN)
if [ -n "$E3" ]; then
  [ "$E3" = "$S1" ] || { echo "ERROR: BIENESTAR_SYNC_TOKEN difiere del operativo; unificar a mano"; exit 1; }
else
  printf 'BIENESTAR_SYNC_TOKEN=%s\n' "$S1" >> .env
fi
unset S1 S2 S3 B1 E1 E2 E3
grep -q '^BIENESTAR_ALLOWED_CHAT_IDS=' .env || {
  if [ -n "${ALLOWLIST:-}" ]; then
    printf 'BIENESTAR_ALLOWED_CHAT_IDS=%s\n' "$ALLOWLIST" >> .env
  else
    read -rsp "BIENESTAR_ALLOWED_CHAT_IDS: " AL; echo
    [ -n "$AL" ] || { echo "ERROR: vacío"; exit 1; }
    printf 'BIENESTAR_ALLOWED_CHAT_IDS=%s\n' "$AL" >> .env
    unset AL
  fi
}
grep -q '^BIENESTAR_DOMAIN_URL=' .env || printf 'BIENESTAR_DOMAIN_URL=http://senda:8000\n' >> .env
chmod 600 .env
echo "claves presentes (nombres): $(grep -o '^[A-Za-z_]*=' .env | grep -E 'SENDA|BIENESTAR|TS_AUTHKEY' | tr '\n' ' ')"

echo "== [5/7] validación de configuración (sin crear nada) =="
$COMPOSE config --quiet && echo "compose válido"

echo "== [6/7] construcción de imágenes (sin arrancar) =="
$COMPOSE build senda
$COMPOSE build app

echo "== [7/7] estado final: nada en ejecución nuevo =="
$COMPOSE ps
unset ALLOWLIST
echo "PREPARACIÓN OK. Corte (up/serve/arranque) solo con confirmación."
echo "Rollback exacto de esta ejecución:"
echo "  bash ops/proxy/rollback-senda.sh \"$BK\""
