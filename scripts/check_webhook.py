import asyncio
import logging
import sys
from pprint import pprint

# Añadir directorio raíz al path
sys.path.append(".")

import httpx

from src.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("webhook_check")


async def check_webhook():
    bot_token = settings.TELEGRAM_BOT_TOKEN.get_secret_value()
    url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url)
            data = resp.json()

            print("\n--- Telegram Webhook Status ---")
            if data.get("ok"):
                result = data["result"]
                pprint(result)

                pending = result.get("pending_update_count", 0)
                if pending > 0:
                    logger.warning(
                        f"⚠️  HAY {pending} MENSAJES PENDIENTES EN COLA DE TELEGRAM!"
                    )
                else:
                    logger.info("✅ Cola de Telegram vacía.")
            else:
                logger.error(f"Error consultando API: {data}")

        except Exception as e:
            logger.error(f"Fallo de conexión: {e}")


if __name__ == "__main__":
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error("No TELEGRAM_BOT_TOKEN in .env")
        sys.exit(1)

    asyncio.run(check_webhook())
