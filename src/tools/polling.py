# Polling Service v0.1.6 - Added Proxy Support for GCE
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
        # Configurar Proxy si está definido en el entorno (Útil para GCE bloqueados)
        proxy_url = os.getenv("TELEGRAM_PROXY") or os.getenv("https_proxy") or os.getenv("HTTPS_PROXY")
        
        # Usamos un opener específico si hay proxy y es para Telegram
        opener = urllib.request.build_opener()
        if proxy_url and "api.telegram.org" in url:
             proxy_handler = urllib.request.ProxyHandler({'http': proxy_url, 'https': proxy_url})
             opener = urllib.request.build_opener(proxy_handler)

        req = urllib.request.Request(url, method=method)
        req.add_header('Content-Type', 'application/json')
        
        if data:
            json_data = json.dumps(data).encode('utf-8')
            req.data = json_data
            
        # Abrir la petición usando el opener local (evita contaminar el proceso global)
        with opener.open(req, timeout=timeout) as response:
            if method == "POST" and response.status not in [200, 202]:
                print(f"Error {response.status}: {response.read().decode()}")
                return None
            return json.loads(response.read().decode())
    except urllib.error.URLError as e:
        if "api.telegram.org" in url:
            print(f"FALLO DE RED TELEGRAM: {e.reason}")
            if "Network is unreachable" in str(e.reason):
                 print("CONSEJO: Tu instancia no tiene salida a Telegram. Prueba configurando TELEGRAM_PROXY en tu .env")
        return None
    except urllib.error.HTTPError as e:
        # Ignorar 409 o errores esperados en webhook delete
        if "deleteWebhook" in url:
            return None
        print(f"HTTP Error {e.code} en {url}: {e.reason}")
        return None
    except Exception as e:
        print(f"Error inesperado en {url}: {e}")
        return None

# --- Main Logic ---

# Cargar configuración
load_env_file()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = "http://127.0.0.1:8000/api/v1/webhooks/telegram"

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
    update_id = update.get('update_id')
    print(f"Forwarding Update {update_id} to {API_URL}...")
    try:
        result = make_request(API_URL, method="POST", data=update, timeout=15)
        if result:
            print(f"✅ Update {update_id} successfully forwarded and processed.")
        else:
            print(f"❌ ERROR: Local API at {API_URL} failed to process Update {update_id}.")
            print(f"   Check if the bot container is running and port 8000 is exposed.")
    except Exception as e:
        print(f"❌ CRITICAL ERROR forwarding Update {update_id}: {e}")

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
            if updates is None:
                print("⚠️ Warning: No response from Telegram. Possible network issue or rate limit.")
                time.sleep(5)
                continue
                
            if updates.get("ok"):
                result_list = updates.get("result", [])
                if result_list:
                    print(f"Received {len(result_list)} updates from Telegram.")
                for update in result_list:
                    forward_update(update)
                    offset = update["update_id"] + 1
            else:
                error_msg = updates.get("description", "Unknown error")
                print(f"❌ Telegram API Error: {error_msg}")
                time.sleep(5)
        except Exception as e:
            print(f"Error en ciclo principal: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
