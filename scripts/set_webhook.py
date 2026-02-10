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


async def set_webhook():
    bot_token = settings.TELEGRAM_BOT_TOKEN.get_secret_value()
    # Detectar URL pública (Ngrok o Dominio)
    webhook_url = os.getenv("PUBLIC_URL")

    if not webhook_url:
        logger.error(
            "❌ Debes definir la variable de entorno PUBLIC_URL con tu dominio de Ngrok o producción."
        )
        logger.error(
            "Ejemplo: PUBLIC_URL=https://mi-bot.ngrok-free.app python3 scripts/set_webhook.py"
        )
        return

    target_url = f"{webhook_url}/api/v1/webhooks/telegram"
    api_url = f"https://api.telegram.org/bot{bot_token}/setWebhook"

    logger.info(f"Configurando Webhook en: {target_url}")

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(api_url, data={"url": target_url})
            data = resp.json()

            print("\n--- Telegram Webhook Setup ---")
            if data.get("ok"):
                logger.info("✅ Webhook configurado exitosamente!")
                pprint(data["result"])
            else:
                logger.error(f"❌ Error configurando webhook: {data}")

        except Exception as e:
            logger.error(f"Fallo de conexión: {e}")


if __name__ == "__main__":
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error("No TELEGRAM_BOT_TOKEN in .env")
        sys.exit(1)

    asyncio.run(set_webhook())
