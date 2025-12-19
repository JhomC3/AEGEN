import requests
import time
import os
import signal
import sys
from pathlib import Path

# Cargar variables de entorno desde .env si existe
try:
    from dotenv import load_dotenv
    # Subir dos niveles desde src/tools/polling.py para encontrar .env
    dotenv_path = Path(__file__).resolve().parent.parent.parent / ".env"
    load_dotenv(dotenv_path=dotenv_path)
except ImportError:
    pass

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
        # La API de MAGI devuelve 202 (Accepted) para procesos en segundo plano
        response = requests.post(API_URL, json=update)
        if response.status_code not in [200, 202]:
            print(f"Error reenviando a API local (Status {response.status_code}): {response.text}")
        else:
            print(f"Update procesado exitosamente: {update.get('update_id')} (Status {response.status_code})")
    except Exception as e:
        print(f"Error conectando a API local en {API_URL}: {e}")

def main():
    print(f"Iniciando Long Polling para el bot...")
    print(f"Reenviando mensajes a: {API_URL}")
    
    # Primero, limpiar cualquier webhook existente para evitar conflictos
    try:
        requests.post(f"{TELEGRAM_API}/deleteWebhook", timeout=10)
        print("Webhook eliminado (pasando a modo polling).")
    except Exception as e:
        print(f"Aviso: No se pudo eliminar el webhook (puede que ya esté libre o no haya red): {e}")

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
