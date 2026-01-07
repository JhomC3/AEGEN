
import os
import sys
import json
import urllib.request
import urllib.error
from pathlib import Path

# Load settings to get tokens
sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.core.config import settings

def test_telegram():
    print("\n--- 1. Testing Telegram Connectivity ---")
    token = settings.TELEGRAM_BOT_TOKEN.get_secret_value() if settings.TELEGRAM_BOT_TOKEN else None
    if not token:
        print("❌ ERROR: TELEGRAM_BOT_TOKEN not found in settings.")
        return False
    
    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
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
    token = settings.TELEGRAM_BOT_TOKEN.get_secret_value() if settings.TELEGRAM_BOT_TOKEN else None
    url = f"https://api.telegram.org/bot{token}/getWebhookInfo"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
            if data.get("ok"):
                info = data["result"]
                url = info.get("url", "")
                if url:
                    print(f"⚠️ STATUS: Webhook is currently set to: {url}")
                    print("   NOTE: If you want to use Polling, you must delete this webhook.")
                else:
                    print("✅ STATUS: No webhook set. Ready for Polling.")
                return True
    except Exception as e:
        print(f"❌ ERROR checking webhook info: {e}")
        return False

def check_model():
    print("\n--- 4. Checking Gemini Model ---")
    model = settings.DEFAULT_LLM_MODEL
    print(f"🔍 Current model configured: {model}")
    print("   Note: If the bot hits the server but never replies, this might be the cause.")

if __name__ == "__main__":
    print("========================================")
    print("      AEGEN DIAGNOSTIC TOOL v1.0       ")
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
