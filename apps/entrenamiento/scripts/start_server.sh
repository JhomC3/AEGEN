#!/bin/bash
# Arranca el servidor del dashboard con el token de HealthSync persistente.
#
# Fuente única de secretos (nunca se imprimen valores):
#   1. Variable explícita (despliegues: SENDA_SYNC_TOKEN / SENDA_CSRF_SECRET),
#      que se persiste en data/ para que el arranque sea idempotente.
#   2. Fichero existente en data/ (reutilización: el teléfono no se toca).
#   3. Generación aleatoria solo si no hay nada (primer arranque en desarrollo).
# La app debug consume el token en build-time (BuildConfig.DEFAULT_SYNC_TOKEN).
# - Genera y persiste el secreto CSRF (data/csrf_secret, no se imprime) y activa
#   el modo LAN sync-only: en la LAN solo se sirve POST /sync/health-connect.
# - Logs de acceso SIN buffer (PYTHONUNBUFFERED) para ver las peticiones en vivo.
set -euo pipefail
cd "$(dirname "$0")/.."

umask 077

TOKEN_FILE="data/hc_sync_token"
if [ -n "${SENDA_SYNC_TOKEN:-}" ]; then
    printf '%s' "$SENDA_SYNC_TOKEN" > "$TOKEN_FILE"
elif [ ! -f "$TOKEN_FILE" ]; then
    openssl rand -hex 32 > "$TOKEN_FILE"
    echo "=== Token nuevo en $TOKEN_FILE (no se muestra; recompila el APK debug para usarlo). ==="
fi

SECRET_FILE="data/csrf_secret"
if [ -n "${SENDA_CSRF_SECRET:-}" ]; then
    printf '%s' "$SENDA_CSRF_SECRET" > "$SECRET_FILE"
elif [ ! -f "$SECRET_FILE" ]; then
    openssl rand -hex 48 > "$SECRET_FILE"
    echo "=== Secreto CSRF nuevo en $SECRET_FILE (no se muestra). ==="
fi
if [ ! -s "$SECRET_FILE" ] || [ ! -s "$TOKEN_FILE" ]; then
    echo "error: secreto vacío; bórralo para regenerarlo." >&2
    exit 1
fi

exec env PYTHONUNBUFFERED=1 \
    HC_SYNC_TOKEN="$(cat "$TOKEN_FILE")" \
    GYM_CSRF_SECRET="$(cat "$SECRET_FILE")" \
    GYM_LAN_SYNC_ONLY=1 \
    uv run uvicorn app:app --host 0.0.0.0 --port 8000 --access-log --no-proxy-headers
# NOTA: --no-proxy-headers es EXPLÍCITO y obligatorio en senda (no basta con
# omitir --proxy-headers: el default podría cambiar y FORWARDED_ALLOW_IPS solo
# actúa con el middleware instalado). Con --proxy-headers, uvicorn reescribe
# scope['client'] desde X-Forwarded-For cuando el peer es loopback, y el proxy
# de Tailscale añade ahí la IP tailnet del cliente: el gate vería 100.x en
# lugar de 127.0.0.1 y rechazaría el dashboard servido (403 real observado).
# Comportamiento verificado con uvicorn 0.52.1 (uv.lock) en tests; el bloque
# de despliegue aborta si la versión instalada en SENDA difiere.
# El scheme tras el proxy TLS lo fija GYM_BEHIND_TLS_PROXY (compose), no XFP.
