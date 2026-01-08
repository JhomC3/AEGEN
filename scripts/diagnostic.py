
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
            # Use 'state' or 'message' instead of 'status' which doesn't exist
            status_val = data.get('state') or "UP"
            print(f"✅ SUCCESS: Local API is healthy. State: {status_val}")
            return True
    except Exception as e:
        print(f"❌ ERROR: Could not reach Local API at 127.0.0.1:8000: {e}")
        print("   TIP: Make sure your docker containers are running (`docker-compose ps`).")
        return False

def check_polling_process():
    print("\n--- 3. Checking Polling Process ---")
    try:
        # We try to run a command to find the process. 
        # Note: This works on Linux/Mac if running on the same host.
        import subprocess
        result = subprocess.run(['pgrep', '-f', 'src/tools/polling.py'], capture_output=True, text=True)
        if result.stdout.strip():
            print(f"✅ SUCCESS: Polling service is RUNNING (PID: {result.stdout.strip()})")
            return True
        else:
            print("❌ ERROR: Polling service is NOT running.")
            print("   FIX: Run `sudo systemctl start aegen-polling` or `python3 src/tools/polling.py &`")
            return False
    except Exception:
        print("⚠️ Warning: Could not check process list (pgrep not available?)")
        return None

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
    api_key = os.getenv("GOOGLE_API_KEY")
    print(f"🔍 Current model configured: {model}")
    
    if not api_key:
        print("⚠️ Warning: GOOGLE_API_KEY not found in environment. Cannot verify model availability.")
        return
        
    print("🧪 Testing model availability with a small request...")
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        m = genai.GenerativeModel(model)
        # Just a very simple probe
        m.count_tokens("probe")
        print(f"✅ SUCCESS: Model '{model}' is VALID and reachable.")
    except ImportError:
        print("⚠️ Warning: 'google-generativeai' not installed. Could not probe API directly.")
        print("   TIP: You can run `python3 scripts/list_models.py` if you have it installed.")
    except Exception as e:
        print(f"❌ ERROR: Model '{model}' failed the availability test: {e}")
        print("   ACTION: Check the model name or run `python3 scripts/list_models.py` to see valid options.")

if __name__ == "__main__":
    load_env_file()
    print("========================================")
    print("      AEGEN DIAGNOSTIC TOOL v1.1       ")
    print("      (Standard Library Edition)       ")
    print("========================================")
    
    t_ok = test_telegram()
    l_ok = test_local_api()
    p_ok = check_polling_process()
    w_ok = test_webhook_status()
    check_model()
    
    print("\n========================================")
    if t_ok and l_ok and p_ok:
        print("✅ Core connectivity looks GOOD.")
        print("👉 If it still doesn't work, check the logs of your polling process.")
    else:
        print("❌ Issues detected. Please fix the items marked with ❌.")
    print("========================================")
