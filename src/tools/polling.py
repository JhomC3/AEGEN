import requests
import time
import os
import signal
import sys

# Configuración
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = "http://localhost:8000/api/v1/webhooks/telegram"
TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"

if not TOKEN:
    print("Error: TELEGRAM_BOT_TOKEN no encontrado. Ejecuta 'export TELEGRAM_BOT_TOKEN=...' primero.")
    sys.exit(1)

def signal_handler(sig, frame):
    print("\nDeteniendo polling...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def get_updates(offset=None):
    url = f"{TELEGRAM_API}/getUpdates"
    params = {"timeout": 30, "allowed_updates": ["message", "edited_message"]}
    if offset:
        params["offset"] = offset
    try:
        response = requests.get(url, params=params, timeout=35)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error conectando a Telegram: {e}")
        time.sleep(5)
        return None

def forward_update(update):
    try:
        # Reenviar el update tal cual lo recibe a nuestra API local
        # Nuestra API espera el JSON del update en el body
        response = requests.post(API_URL, json=update)
        if response.status_code != 200:
            print(f"Error reenviando a API local: {response.text}")
        else:
            print(f"Update procesado: {update.get('update_id')}")
    except Exception as e:
        print(f"Error conectando a API local: {e}")

def main():
    print(f"Iniciando Long Polling para el bot...")
    print(f"Reenviando mensajes a: {API_URL}")
    
    # Primero, limpiar cualquier webhook existente para evitar conflictos
    requests.post(f"{TELEGRAM_API}/deleteWebhook")
    print("Webhook eliminado (pasando a modo polling).")

    offset = None
    while True:
        updates = get_updates(offset)
        if updates and updates.get("ok"):
            for update in updates.get("result", []):
                forward_update(update)
                offset = update["update_id"] + 1
        time.sleep(0.1)

if __name__ == "__main__":
    main()
