import json
import os
import socket
import urllib.request
from pathlib import Path


def load_env():
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        print("❌ No se encontró .env")
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key] = val.strip().strip("'").strip('"')


def test_connectivity():
    print("--- 🩺 Diagnóstico de Red AEGEN ---")

    # 1. DNS
    print("\n1. Probando DNS (api.telegram.org)...")
    try:
        ip = socket.gethostbyname("api.telegram.org")
        print(f"✅ DNS OK: api.telegram.org -> {ip}")
    except Exception as e:
        print(f"❌ DNS FALLÓ: {e}")

    # 2. Conexión básica HTTPS
    print("\n2. Probando conexión HTTPS básica...")
    try:
        resp = urllib.request.urlopen("https://api.telegram.org", timeout=10)
        print(f"✅ Conexión básica OK (Status: {resp.status})")
    except Exception as e:
        print(f"❌ Conexión básica FALLÓ: {e}")

    # 3. Validar Token
    load_env()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("\n3. ❌ TELEGRAM_BOT_TOKEN no encontrado en .env")
    else:
        token = token.strip()
        print(f"\n3. Probando Token (Longitud: {len(token)})...")
        url = f"https://api.telegram.org/bot{token}/getMe"
        try:
            resp = urllib.request.urlopen(url, timeout=10)
            data = json.loads(resp.read().decode())
            if data.get("ok"):
                print(f"✅ Token VÁLIDO: @{data['result']['username']}")
            else:
                print(f"❌ Token INVÁLIDO: {data.get('description')}")
        except Exception as e:
            print(f"❌ Error probando Token: {e}")

    # 4. API Local
    print("\n4. Probando API Local (AEGEN Docker)...")
    try:
        resp = urllib.request.urlopen("http://127.0.0.1:8000/system/health", timeout=5)
        print(f"✅ API Local OK (Status: {resp.status})")
    except Exception as e:
        print(f"❌ API Local NO RESPONDE: {e}")
        print("   Asegúrate de que 'docker-compose up' esté corriendo.")


if __name__ == "__main__":
    test_connectivity()
