import asyncio
import os
import signal
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Cargar variables de entorno
try:
    dotenv_path = Path(__file__).resolve().parent.parent.parent / ".env"
    load_dotenv(dotenv_path=dotenv_path)
except ImportError:
    pass

# Configuración
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = "http://localhost:8000/api/v1/webhooks/telegram"
TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"

if not TOKEN:
    print("Error: TELEGRAM_BOT_TOKEN no encontrado.")
    sys.exit(1)


async def delete_webhook():
    async with httpx.AsyncClient() as client:
        try:
            await client.post(f"{TELEGRAM_API}/deleteWebhook", timeout=10.0)
            print("Webhook eliminado (pasando a modo polling).")
        except Exception as e:
            print(f"Aviso: No se pudo eliminar el webhook: {e}")


async def get_updates(offset=None):
    url = f"{TELEGRAM_API}/getUpdates"
    params = {"timeout": 30, "allowed_updates": ["message", "edited_message"]}
    if offset:
        params["offset"] = offset
    
    async with httpx.AsyncClient(timeout=35.0) as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error conectando a Telegram: {e}")
            await asyncio.sleep(5)
            return None


async def forward_update(update):
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(API_URL, json=update)
            if response.status_code not in [200, 202]:
                print(f"Error reenviando (Status {response.status_code}): {response.text}")
            else:
                print(f"Update procesado: {update.get('update_id')}")
        except Exception as e:
            print(f"Error reenviando a API local: {e}")


async def main_loop():
    print("Iniciando Long Polling (Async) para el bot...")
    print(f"Reenviando mensajes a: {API_URL}")

    await delete_webhook()

    offset = None
    while True:
        updates = await get_updates(offset)
        if updates and updates.get("ok"):
            for update in updates.get("result", []):
                await forward_update(update)
                offset = update["update_id"] + 1
        else:
            await asyncio.sleep(0.1)


def main():
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        print("\nDeteniendo polling...")
        sys.exit(0)


if __name__ == "__main__":
    main()
