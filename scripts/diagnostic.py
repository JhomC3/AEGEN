
import os
import sys
import json
import urllib.request
import urllib.error
from pathlib import Path

# --- Utils to avoid external dependencies like python-dotenv ---

def load_env_file():
    """Manually loads .env variables."""
    try:
        env_path = Path(__file__).resolve().parent.parent / ".env"
        if not env_path.exists():
            print("⚠️ Warning: .env file not found at", env_path)
            return
        
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # Handle 'export ' prefix
                if line.startswith("export "):
                    line = line.replace("export ", "", 1)
                
                if "=" in line:
                    key, value = line.split("=", 1)
                    # Clean quotes
                    value = value.strip().strip("'").strip('"')
                    os.environ[key] = value
    except Exception as e:
        print(f"Warning: Could not read .env: {e}")

# --- Diagnostic Tests ---

def test_telegram():
    print("\n--- 1. Testing Telegram Connectivity ---")
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ ERROR: TELEGRAM_BOT_TOKEN not found in .env")
        return False
    
    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        # Check for proxy
        proxy_url = os.getenv("TELEGRAM_PROXY") or os.getenv("https_proxy") or os.getenv("HTTPS_PROXY")
        opener = urllib.request.build_opener()
        if proxy_url:
            print(f"   ℹ️ Using proxy: {proxy_url}")
            proxy_handler = urllib.request.ProxyHandler({'http': proxy_url, 'https': proxy_url})
            opener = urllib.request.build_opener(proxy_handler)

        with opener.open(url, timeout=10) as response:
            data = json.loads(response.read().decode())
            if data.get("ok"):
                bot_info = data["result"]
                print(f"✅ SUCCESS: Bot is alive! Name: @{bot_info.get('username')}")
                return True
            else:
                print(f"❌ ERROR: Telegram returned error: {data.get('description')}")
                return False
    except Exception as e:
        print(f"❌ ERROR: Could not reach Telegram: {e}")
        print("   TIP: If you are on GCE, you might need a proxy (TELEGRAM_PROXY).")
        return False

def test_local_api():
    print("\n--- 2. Testing Local API Reachability ---")
    url = "http://127.0.0.1:8000/system/status"
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode())
            print(f"✅ SUCCESS: Local API is healthy. Status: {data.get('status')}")
            return True
    except Exception as e:
        print(f"❌ ERROR: Could not reach Local API at 127.0.0.1:8000: {e}")
        print("   TIP: Make sure your docker containers are running (`docker-compose ps`).")
        return False

def test_webhook_status():
    print("\n--- 3. Checking Webhook Status ---")
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        return False
        
    url = f"https://api.telegram.org/bot{token}/getWebhookInfo"
    try:
        # Use simple opener for this check, or reuse proxy logic if needed
        proxy_url = os.getenv("TELEGRAM_PROXY") or os.getenv("https_proxy") or os.getenv("HTTPS_PROXY")
        opener = urllib.request.build_opener()
        if proxy_url:
             proxy_handler = urllib.request.ProxyHandler({'http': proxy_url, 'https': proxy_url})
             opener = urllib.request.build_opener(proxy_handler)

        with opener.open(url, timeout=10) as response:
            data = json.loads(response.read().decode())
            if data.get("ok"):
                info = data["result"]
                url_set = info.get("url", "")
                if url_set:
                    print(f"⚠️ STATUS: Webhook is currently set to: {url_set}")
                    print("   NOTE: If you want to use Polling, you must delete this webhook.")
                    print("   FIX: The polling script usually deletes this automatically on start.")
                else:
                    print("✅ STATUS: No webhook set. Ready for Polling.")
                return True
    except Exception as e:
        print(f"❌ ERROR checking webhook info: {e}")
        return False

def check_model():
    print("\n--- 4. Checking Gemini Model ---")
    model = os.getenv("DEFAULT_LLM_MODEL", "gemini-2.5-flash-lite")
    print(f"🔍 Current model configured: {model}")

if __name__ == "__main__":
    load_env_file()
    print("========================================")
    print("      AEGEN DIAGNOSTIC TOOL v1.1       ")
    print("      (Standard Library Edition)       ")
    print("========================================")
    
    t_ok = test_telegram()
    l_ok = test_local_api()
    w_ok = test_webhook_status()
    check_model()
    
    print("\n========================================")
    if t_ok and l_ok:
        print("✅ Core connectivity looks GOOD.")
        print("👉 If it still doesn't work, check the logs of your polling process.")
    else:
        print("❌ Issues detected. Please fix the items marked with ❌.")
    print("========================================")
