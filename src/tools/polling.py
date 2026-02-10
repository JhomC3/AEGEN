# Polling Service v0.4.1 - GCE Optimized (StdLib)
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
    """Carga variables de .env manualmente."""
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
                key, value = line.split("=", 1)
                os.environ[key] = value.strip().strip("'").strip('"')
    except Exception as e:
        logger.warning(f"No se pudo leer .env: {e}")


def make_request(url, method="GET", data=None, timeout=30):
    """Realiza peticiones HTTP robustas."""
    # Limpiar URL por si acaso hay espacios invisibles
    url = url.strip()
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
            logger.warning(
                f"Fallo de red temporal en Telegram ({type(e.reason).__name__}): {e.reason}"
            )
        else:
            logger.error(f"Error conectando a API Local: {e.reason}")
        return None
    except urllib.error.HTTPError as e:
        if "deleteWebhook" in url and e.code == 404:
            return None
        logger.error(f"HTTP Error {e.code} en {url}: {e.reason}")
        return None
    except Exception as e:
        logger.error(f"Error inesperado ({type(e).__name__}) en {url}: {e}")
        return None


# --- Main Logic ---
load_env_file()
# FORZAR STRIP DEL TOKEN (podría venir con espacios del EnvironmentFile)
TOKEN_RAW = os.getenv("TELEGRAM_BOT_TOKEN")
TOKEN = TOKEN_RAW.strip() if TOKEN_RAW else None
API_URL = os.getenv("LOCAL_API_URL", "http://127.0.0.1:8000/api/v1/webhooks/telegram")

if not TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN no encontrado. Verifica tu .env o systemd unit.")
    sys.exit(1)

TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"
POLLING_TIMEOUT = 25


def delete_webhook():
    logger.info("Eliminando webhook existente...")
    make_request(f"{TELEGRAM_API}/deleteWebhook", method="POST", timeout=10)


def get_updates(offset=None):
    url = f"{TELEGRAM_API}/getUpdates?timeout={POLLING_TIMEOUT}"
    if offset:
        url += f"&offset={offset}"
    return make_request(url, timeout=POLLING_TIMEOUT + 5)


def forward_update(update):
    """Reenvía update a API local."""
    update_id = update.get("update_id")
    try:
        result = make_request(API_URL, method="POST", data=update, timeout=5)
        if result is not None:
            logger.info(f"✅ Update {update_id} -> API Local: OK")
            return True
        else:
            logger.warning(f"❌ Update {update_id} -> API Local: FALLÓ")
            return False
    except Exception as e:
        logger.error(f"❌ Error crítico reenviando Update {update_id}: {e}")
        return False


def main():
    logger.info(
        f"Iniciando Polling Service v0.4.1 (GCE Optimized / Timeout={POLLING_TIMEOUT}s)"
    )
    logger.info(f"Token (masked): {TOKEN[:10]}...{TOKEN[-5:]}")
    logger.info(f"Target API: {API_URL}")

    def signal_handler(sig, frame):
        logger.info("🛑 Deteniendo servicio de polling...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    delete_webhook()

    offset = None
    consecutive_errors = 0

    while True:
        try:
            updates = get_updates(offset)

            if updates is None:
                consecutive_errors += 1
                sleep_time = min(2 * consecutive_errors, 30)
                logger.warning(
                    f"⚠️ Error de conexión #{consecutive_errors}. Esperando {sleep_time}s..."
                )
                time.sleep(sleep_time)
                continue

            if consecutive_errors > 0:
                logger.info("🟢 Conexión con Telegram restablecida.")
                consecutive_errors = 0

            if updates.get("ok"):
                result_list = updates.get("result", [])
                for update in result_list:
                    success = forward_update(update)
                    if success:
                        offset = update["update_id"] + 1
                    else:
                        logger.info("⏳ API Local no disponible. Reintentando en 5s...")
                        time.sleep(5)
                        break
            else:
                error_msg = updates.get("description", "Unknown error")
                error_code = updates.get("error_code")
                logger.error(f"❌ Telegram API Error {error_code}: {error_msg}")
                time.sleep(5)

        except Exception as e:
            logger.error(f"🔥 Error no controlado: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
