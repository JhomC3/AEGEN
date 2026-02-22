import asyncio
import logging
import os
import sys
from pprint import pprint

# Añadir directorio raíz al path
sys.path.append(".")

import httpx

from src.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("webhook_setup")


async def set_webhook() -> None:
    """Configura el webhook de Telegram."""
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error("No TELEGRAM_BOT_TOKEN")
        return

    bot_token = settings.TELEGRAM_BOT_TOKEN.get_secret_value()
    webhook_url = os.getenv("PUBLIC_URL")

    if not webhook_url:
        logger.error("❌ PUBLIC_URL no definida.")
        return

    target_url = f"{webhook_url}/api/v1/webhooks/telegram"
    api_url = f"https://api.telegram.org/bot{bot_token}/setWebhook"

    logger.info("Configurando Webhook en: %s", target_url)

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(api_url, data={"url": target_url})
            data = resp.json()

            if data.get("ok"):
                logger.info("✅ Webhook configurado exitosamente!")
                pprint(data["result"])
            else:
                logger.error("❌ Error configurando webhook: %s", data)
        except Exception as e:
            logger.error("Fallo de conexión: %s", e)


if __name__ == "__main__":
    asyncio.run(set_webhook())
