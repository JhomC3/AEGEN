from __future__ import annotations

import logging
import os
import signal
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

from src.tools.telegram.client import POLLING_TIMEOUT, PersistentTelegramClient
from src.tools.telegram.forwarder import forward_to_local_api

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("polling_service")


def load_env_file() -> None:
    """Carga variables de .env manualmente."""
    try:
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
        if not env_path.exists():
            return
        content = env_path.read_text()
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ[key] = value.strip().strip("'").strip('"')
    except Exception as e:
        logger.warning("No se pudo leer .env: %s", e)


load_env_file()
TOKEN_RAW = os.getenv("TELEGRAM_BOT_TOKEN")
TOKEN = TOKEN_RAW.strip() if TOKEN_RAW else None
API_URL = os.getenv("LOCAL_API_URL", "http://127.0.0.1:8000/api/v1/webhooks/telegram")

if not TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN no encontrado.")
    sys.exit(1)


def process_updates(updates: dict, offset: int | None) -> int | None:
    """Procesa los updates recibidos de Telegram."""
    if not updates.get("ok"):
        error_code = updates.get("error_code")
        error_msg = updates.get("description", "Unknown")
        logger.error("Telegram Error %s: %s", error_code, error_msg)
        time.sleep(10 if error_code == 409 else 5)
        return offset

    for update in updates.get("result", []):
        if forward_to_local_api(update, API_URL):
            offset = update["update_id"] + 1
        else:
            logger.info("⏳ API Local no disponible. Reintentando...")
            time.sleep(5)
            break

    return offset


def polling_loop(client: PersistentTelegramClient) -> None:
    """Bucle principal de polling."""
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
                wait = min(2 * consecutive_errors, 30)
                logger.warning("Error #%d. Esperando %ds", consecutive_errors, wait)
                time.sleep(wait)
                continue

            if consecutive_errors > 0:
                logger.info("🟢 Conexión restablecida.")
                consecutive_errors = 0

            offset = process_updates(updates, offset)

        except Exception as e:
            logger.error("🔥 Error no controlado: %s", e)
            time.sleep(5)


def main() -> None:
    """Punto de entrada."""
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN es None. Abortando.")
        sys.exit(1)

    logger.info("Iniciando Polling Service v0.5.0")

    # Esperar a que la API local esté disponible antes de iniciar el polling
    # Esto evita el loop de "API Local no disponible" cuando la app aún
    # no ha completado su inicialización (cold start ~120s con ingesta de PDFs)
    logger.info("Esperando disponibilidad de API local en %s ...", API_URL)
    startup_retries = 0
    while startup_retries < 60:  # ~5 minutos máximo de espera
        try:
            req = urllib.request.Request(API_URL, method="POST")  # noqa: S310
            req.add_header("Content-Type", "application/json")
            req.data = b"{}"
            with urllib.request.urlopen(req, timeout=3) as resp:  # noqa: S310
                if resp.status in (200, 202):
                    logger.info("API local disponible. Iniciando polling...")
                    break
        except Exception as e:
            logger.debug("API local aún no disponible: %s", e)
        startup_retries += 1
        if startup_retries % 6 == 0:
            logger.info("Esperando API local... (intento %d/60)", startup_retries)
        time.sleep(5)
    else:
        logger.warning(
            "No se pudo conectar a la API local tras %d intentos. "
            "Iniciando polling de todas formas...",
            startup_retries,
        )

    client = PersistentTelegramClient(TOKEN)

    def sig_handler(sig: int, frame: Any) -> None:
        client.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    client.request("deleteWebhook")
    polling_loop(client)


if __name__ == "__main__":
    main()
