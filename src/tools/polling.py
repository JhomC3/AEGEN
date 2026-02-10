# Polling Service v0.2.0 - Async & Resilient
import asyncio
import logging
import os
import signal
import sys
from pathlib import Path
from typing import Any, Optional

import httpx

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


# --- Core Service ---


class PollingService:
    def __init__(self):
        load_env_file()
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.api_url = os.getenv(
            "LOCAL_API_URL", "http://127.0.0.1:8000/api/v1/webhooks/telegram"
        )
        self.proxy = (
            os.getenv("TELEGRAM_PROXY")
            or os.getenv("https_proxy")
            or os.getenv("HTTPS_PROXY")
        )

        if not self.token:
            logger.error("TELEGRAM_BOT_TOKEN no encontrado en .env")
            sys.exit(1)

        self.telegram_api = f"https://api.telegram.org/bot{self.token}"
        self.offset = None
        self.running = True

        # Cliente HTTP asíncrono persistente
        self.client = httpx.AsyncClient(
            proxy=self.proxy if self.proxy else None,
            timeout=httpx.Timeout(40.0, connect=10.0),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )

    async def shutdown(self):
        """Cierre limpio del servicio."""
        logger.info("Deteniendo servicio de polling...")
        self.running = False
        await self.client.aclose()

    async def make_telegram_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[dict[str, Any]] = None,
    ):
        """Realiza peticiones a la API de Telegram."""
        url = f"{self.telegram_api}/{endpoint}"
        try:
            if method == "POST":
                resp = await self.client.post(url, json=data)
            else:
                resp = await self.client.get(url, params=data)

            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Error en Telegram {endpoint}: {e}")
            return None

    async def forward_to_local_api(self, update: dict):
        """Envía el update a la API de AEGEN de forma asíncrona."""
        update_id = update.get("update_id")
        logger.info(f"Forwarding Update {update_id}...")

        try:
            # Petición local (sin proxy)
            async with httpx.AsyncClient(timeout=20.0) as local_client:
                resp = await local_client.post(self.api_url, json=update)
                if resp.status_code in [200, 202]:
                    logger.info(f"✅ Update {update_id} enviado exitosamente.")
                    return True
                else:
                    logger.error(
                        f"❌ API Local respondió {resp.status_code}: {resp.text}"
                    )
                    return False
        except Exception as e:
            logger.error(f"❌ Error crítico reenviando Update {update_id}: {e}")
            return False

    async def run(self):
        logger.info("Iniciando Polling Service v0.2.0 (Async)...")
        logger.info(f"Target API: {self.api_url}")
        if self.proxy:
            logger.info(f"Proxy detectado: {self.proxy}")

        # Limpiar webhooks previos para permitir polling
        await self.make_telegram_request("POST", "deleteWebhook")

        while self.running:
            try:
                params = {"timeout": 30}
                if self.offset:
                    params["offset"] = self.offset

                updates_resp = await self.make_telegram_request(
                    "GET", "getUpdates", params
                )

                if not updates_resp or not updates_resp.get("ok"):
                    await asyncio.sleep(5)
                    continue

                updates = updates_resp.get("result", [])
                if updates:
                    logger.info(f"Recibidos {len(updates)} updates.")

                for update in updates:
                    success = await self.forward_to_local_api(update)
                    if success:
                        # Solo incrementamos el offset si se entregó con éxito
                        # Esto asegura que si la API está reiniciando, el mensaje se reintente
                        self.offset = update["update_id"] + 1
                    else:
                        # Si falló, esperamos un poco y NO incrementamos offset
                        # El siguiente getUpdates volverá a traer este mismo mensaje
                        logger.warning(
                            f"Retrasando offset para reintentar update {update['update_id']}"
                        )
                        await asyncio.sleep(2)
                        break  # Salimos del bucle para re-consultar Telegram

            except Exception as e:
                logger.error(f"Error en bucle principal: {e}")
                await asyncio.sleep(5)


# --- Entrypoint ---


async def main():
    service = PollingService()

    # Manejo de señales
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(service.shutdown()))

    try:
        await service.run()
    except asyncio.CancelledError:
        pass
    finally:
        await service.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
