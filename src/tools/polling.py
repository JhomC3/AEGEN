import json
import os
import signal
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

# --- Utils para no depender de librerías externas ---

def load_env_file():
    """Carga variables de .env manualmente para no depender de python-dotenv"""
    try:
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
        if not env_path.exists():
            return
        
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" in line and line.startswith("export "):
                    line = line.replace("export ", "", 1) # Remove 'export ' prefix
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                # Limpiar comillas si existen
                value = value.strip().strip("'").strip('"')
                os.environ[key] = value
    except Exception as e:
        print(f"Warning: No se pudo leer .env: {e}")

def make_request(url, method="GET", data=None, timeout=30):
    """Realiza peticiones HTTP usando solo la librería estándar"""
    try:
        req = urllib.request.Request(url, method=method)
        req.add_header('Content-Type', 'application/json')
        
        if data:
            json_data = json.dumps(data).encode('utf-8')
            req.data = json_data
            
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if method == "POST" and response.status not in [200, 202]:
                print(f"Error {response.status}: {response.read().decode()}")
                return None
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        # Ignorar 409 o errores esperados en webhook delete
        if "deleteWebhook" in url:
            return None
        print(f"HTTP Error {e.code} en {url}: {e.reason}")
        return None
    except Exception as e:
        print(f"Error conexión {url}: {e}")
        return None

# --- Main Logic ---

# Cargar configuración
load_env_file()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = "http://localhost:8000/api/v1/webhooks/telegram"

if not TOKEN:
    print("Error: TELEGRAM_BOT_TOKEN no encontrado en .env")
    sys.exit(1)

TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"

def delete_webhook():
    print("Eliminando webhook existente...")
    make_request(f"{TELEGRAM_API}/deleteWebhook", method="POST")

def get_updates(offset=None):
    url = f"{TELEGRAM_API}/getUpdates?timeout=30"
    if offset:
        url += f"&offset={offset}"
    return make_request(url, timeout=35)

def forward_update(update):
    make_request(API_URL, method="POST", data=update, timeout=10)
    print(f"Update procesado: {update.get('update_id')}")

def main():
    print("Iniciando Polling Service (v0.1.5 - StdLib Only)...")
    print(f"Target: {API_URL}")
    
    # Manejo de señales para salir limpio
    def signal_handler(sig, frame):
        print("\nDeteniendo polling...")
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    delete_webhook()

    offset = None
    while True:
        try:
            updates = get_updates(offset)
            if updates and updates.get("ok"):
                for update in updates.get("result", []):
                    forward_update(update)
                    offset = update["update_id"] + 1
            else:
                time.sleep(1) # Backoff si hay error o no updates
        except Exception as e:
            print(f"Error en ciclo principal: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
