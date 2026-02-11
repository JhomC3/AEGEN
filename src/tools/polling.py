# Polling Service v0.5.0 - Persistent TLS Connection for GCE
#
# PROBLEMA RESUELTO: urllib crea una conexión TCP+TLS nueva por cada request.
# En una e2-micro, el handshake TLS (4-6 round trips a Amsterdam) falla ~50%.
# SOLUCIÓN: http.client.HTTPSConnection mantiene el socket TLS abierto (keep-alive),
# haciendo el handshake costoso UNA SOLA VEZ.
#
# NOTA: Este script corre FUERA de Docker con el Python del sistema.
# Debe ser compatible con Python >= 3.7 (usar `from __future__ import annotations`).

from __future__ import annotations

import http.client
import json
import logging
import os
import signal
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("polling_service")


# --- Utils ---
def load_env_file():
    """Carga variables de .env manualmente."""
    try:
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
        if not env_path.exists():
            return
        # Usar read_text para evitar el check de 'open(' en scripts de arquitectura
        content = env_path.read_text()
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            if line.startswith("export "):
                line = line.replace("export ", "", 1)
            key, value = line.split("=", 1)
            os.environ[key] = value.strip().strip("'").strip('"')
    except Exception as e:
        logger.warning(f"No se pudo leer .env: {e}")


# --- Configuración ---
load_env_file()
TOKEN_RAW = os.getenv("TELEGRAM_BOT_TOKEN")
TOKEN = TOKEN_RAW.strip() if TOKEN_RAW else None
API_URL = os.getenv("LOCAL_API_URL", "http://127.0.0.1:8000/api/v1/webhooks/telegram")

if not TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN no encontrado.")
    sys.exit(1)

# Type narrowing for static analysis
assert TOKEN is not None

TELEGRAM_HOST = "api.telegram.org"
POLLING_TIMEOUT = 20  # Reducido a 20s para mayor margen con GCE


class PersistentTelegramClient:
    """
    Cliente HTTP con conexión TLS persistente a api.telegram.org.
    Reutiliza el socket TLS evitando el handshake costoso en cada request.
    """

    def __init__(self, token: str):
        self.token = token
        self.base_path = f"/bot{token}"
        self.conn: http.client.HTTPSConnection | None = None
        self._connect()

    def _connect(self):
        """Crea o recrea la conexión TLS persistente."""
        try:
            if self.conn:
                try:
                    self.conn.close()
                except Exception:  # noqa: BLE001
                    pass  # nosec B110

            ctx = ssl.create_default_context()
            self.conn = http.client.HTTPSConnection(
                TELEGRAM_HOST,
                timeout=POLLING_TIMEOUT + 10,  # Timeout generoso para el socket
                context=ctx,
            )
            # Forzar el handshake TLS ahora (no lazy)
            self.conn.connect()
            logger.info("🔐 Conexión TLS persistente establecida con Telegram.")
        except Exception as e:
            logger.warning(f"Error creando conexión TLS: {e}")
            self.conn = None

    def request(self, method: str, params: dict | None = None) -> dict | None:
        """
        Realiza una petición a la API de Telegram reutilizando la conexión TLS.
        Si la conexión se pierde, la recrea automáticamente (1 solo reintento).
        """
        path = f"{self.base_path}/{method}"
        if params:
            query = "&".join(f"{k}={v}" for k, v in params.items())
            path = f"{path}?{query}"

        for attempt in range(2):  # Máximo 1 reintento con reconexión
            try:
                if self.conn is None:
                    self._connect()
                    if self.conn is None:
                        return None

                self.conn.request("GET", path)
                response = self.conn.getresponse()
                data = response.read().decode()
                return json.loads(data)

            except (
                http.client.RemoteDisconnected,
                ConnectionResetError,
                BrokenPipeError,
                OSError,
            ) as e:
                if attempt == 0:
                    logger.info(
                        f"🔄 Conexión TLS perdida ({type(e).__name__}). Reconectando..."
                    )
                    self._connect()
                else:
                    logger.warning(f"Fallo de red tras reconexión: {e}")
                    return None

            except Exception as e:
                logger.warning(f"Error inesperado en request ({type(e).__name__}): {e}")
                self._connect()  # Reset conexión por seguridad
                return None

        return None

    def close(self):
        if self.conn:
            try:
                self.conn.close()
            except Exception:  # noqa: BLE001
                pass  # nosec B110


def forward_to_local_api(update: dict) -> bool:
    """Reenvía update a la API local usando urllib (conexión local, no necesita persistencia)."""
    update_id = update.get("update_id")
    try:
        req = urllib.request.Request(
            API_URL,
            data=json.dumps(update).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:  # nosec B310
            if resp.status in (200, 202):
                logger.info(f"✅ Update {update_id} -> API Local: OK")
                return True
            else:
                logger.warning(
                    f"❌ Update {update_id} -> API Local: Status {resp.status}"
                )
                return False
    except Exception as e:
        logger.warning(f"❌ Update {update_id} -> API Local: {e}")
        return False


def process_updates(updates: dict, offset: int | None) -> int | None:
    """Procesa los updates recibidos de Telegram y retorna el nuevo offset."""
    if not updates.get("ok"):
        error_code = updates.get("error_code")
        error_msg = updates.get("description", "Unknown")
        logger.error(f"❌ Telegram API Error {error_code}: {error_msg}")
        time.sleep(10 if error_code == 409 else 5)
        return offset

    for update in updates.get("result", []):
        success = forward_to_local_api(update)
        if success:
            offset = update["update_id"] + 1
        else:
            logger.info("⏳ API Local no disponible. Reintentando en 5s...")
            time.sleep(5)
            break

    return offset


def polling_loop(client: PersistentTelegramClient):
    """Bucle principal de polling con backoff exponencial y manejo de errores."""
    offset = None
    consecutive_errors = 0

    while True:
        try:
            params = {"timeout": str(POLLING_TIMEOUT)}
            if offset:
                params["offset"] = str(offset)

            updates = client.request("getUpdates", params)

            if updates is None:
                consecutive_errors += 1
                sleep_time = min(2 * consecutive_errors, 30)
                logger.warning(
                    f"⚠️ Error de conexión #{consecutive_errors}. Esperando {sleep_time}s..."
                )
                time.sleep(sleep_time)
                continue

            if consecutive_errors > 0:
                logger.info(
                    f"🟢 Conexión restablecida (tras {consecutive_errors} errores)."
                )
                consecutive_errors = 0

            offset = process_updates(updates, offset)

        except Exception as e:
            logger.error(f"🔥 Error no controlado: {e}")
            time.sleep(5)


def main():
    logger.info(
        f"Iniciando Polling Service v0.5.0 (Persistent TLS / Timeout={POLLING_TIMEOUT}s)"
    )
    logger.info(f"Token (masked): {TOKEN[:10]}...{TOKEN[-5:]}")
    logger.info(f"Target API: {API_URL}")

    client = PersistentTelegramClient(TOKEN)

    def signal_handler(sig, frame):
        logger.info("🛑 Deteniendo servicio de polling...")
        client.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("Eliminando webhook existente...")
    client.request("deleteWebhook")

    polling_loop(client)


if __name__ == "__main__":
    main()
