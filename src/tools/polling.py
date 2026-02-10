# Polling Service v0.3.0 - StdLib Only + Resilient Offset
import json
import logging
import os
import signal
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# --- Configuración de Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("polling_service")


# --- Utils ---
def load_env_file():
    """Carga variables de .env manualmente para no depender de python-dotenv."""
    try:
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
        if not env_path.exists():
            return

        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                if line.startswith("export "):
                    line = line.replace("export ", "", 1)
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                value = value.strip().strip("'").strip('"')
                os.environ[key] = value
    except Exception as e:
        logger.warning(f"No se pudo leer .env: {e}")


def make_request(url, method="GET", data=None, timeout=30):
    """Realiza peticiones HTTP usando solo la librería estándar."""
    try:
        proxy_url = (
            os.getenv("TELEGRAM_PROXY")
            or os.getenv("https_proxy")
            or os.getenv("HTTPS_PROXY")
        )

        opener = urllib.request.build_opener()
        if proxy_url and "api.telegram.org" in url:
            proxy_handler = urllib.request.ProxyHandler({
                "http": proxy_url,
                "https": proxy_url,
            })
            opener = urllib.request.build_opener(proxy_handler)

        req = urllib.request.Request(url, method=method)
        req.add_header("Content-Type", "application/json")

        if data:
            json_data = json.dumps(data).encode("utf-8")
            req.data = json_data

        with opener.open(req, timeout=timeout) as response:
            return json.loads(response.read().decode())
    except urllib.error.URLError as e:
        if "api.telegram.org" in url:
            logger.error(f"FALLO DE RED TELEGRAM: {e.reason}")
        return None
    except urllib.error.HTTPError as e:
        if "deleteWebhook" in url:
            return None
        logger.error(f"HTTP Error {e.code} en {url}: {e.reason}")
        return None
    except Exception as e:
        logger.error(f"Error inesperado en {url}: {e}")
        return None


# --- Main Logic ---
load_env_file()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = os.getenv("LOCAL_API_URL", "http://127.0.0.1:8000/api/v1/webhooks/telegram")

if not TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN no encontrado en .env")
    sys.exit(1)

TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"


def delete_webhook():
    logger.info("Eliminando webhook existente...")
    make_request(f"{TELEGRAM_API}/deleteWebhook", method="POST")


def get_updates(offset=None):
    url = f"{TELEGRAM_API}/getUpdates?timeout=30"
    if offset:
        url += f"&offset={offset}"
    return make_request(url, timeout=35)


def forward_update(update):
    """Reenvía un update a la API local. Retorna True si fue exitoso."""
    update_id = update.get("update_id")
    logger.info(f"Forwarding Update {update_id} to {API_URL}...")
    try:
        result = make_request(API_URL, method="POST", data=update, timeout=15)
        if result is not None:
            logger.info(f"✅ Update {update_id} entregado exitosamente.")
            return True
        else:
            logger.error(
                f"❌ API Local no pudo procesar Update {update_id}. "
                f"¿Está el contenedor corriendo y el puerto 8000 expuesto?"
            )
            return False
    except Exception as e:
        logger.error(f"❌ Error crítico reenviando Update {update_id}: {e}")
        return False


def main():
    logger.info("Iniciando Polling Service v0.3.0 (StdLib + Resilient)...")
    logger.info(f"Target: {API_URL}")

    def signal_handler(sig, frame):
        logger.info("Deteniendo polling...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    delete_webhook()

    offset = None
    while True:
        try:
            updates = get_updates(offset)
            if updates is None:
                logger.warning("⚠️ Sin respuesta de Telegram. Posible problema de red.")
                time.sleep(5)
                continue

            if updates.get("ok"):
                result_list = updates.get("result", [])
                if result_list:
                    logger.info(f"Recibidos {len(result_list)} updates de Telegram.")
                for update in result_list:
                    success = forward_update(update)
                    if success:
                        # Solo incrementar offset si la entrega fue exitosa
                        offset = update["update_id"] + 1
                    else:
                        # NO incrementar offset: Telegram reenviará este mensaje
                        logger.warning(
                            f"⏳ Reintentando update {update['update_id']} en 3s..."
                        )
                        time.sleep(3)
                        break  # Salir del for para re-consultar desde este offset
            else:
                error_msg = updates.get("description", "Unknown error")
                logger.error(f"❌ Telegram API Error: {error_msg}")
                time.sleep(5)
        except Exception as e:
            logger.error(f"Error en ciclo principal: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
