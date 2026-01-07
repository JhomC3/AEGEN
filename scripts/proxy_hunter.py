
import urllib.request
import urllib.error
import random
import time
import socket
import ssl
import sys
import os
from pathlib import Path

# --- Configuration ---
TIMEOUT = 5
MAX_PROXIES_TO_TEST = 50
TELEGRAM_TEST_URL = "https://api.telegram.org"

# --- Sources ---
# Free public proxy lists APIs (JSON format preferred)
PROXY_SOURCES = [
    "https://proxylist.geonode.com/api/proxy-list?limit=100&page=1&sort_by=lastChecked&sort_type=desc&protocols=https",
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt", # Text format
]

# Hardcoded fallback list (high quality free proxies often rotate, these might die)
FALLBACK_PROXIES = [
    # Format: host:port
    "20.210.113.32:8123",
    "20.206.106.192:8123",
    "8.219.97.248:80",
]

def load_env_file_manual():
    """Manually loads .env to see if there is already a proxy set."""
    try:
        env_path = Path(__file__).resolve().parent.parent / ".env"
        current_proxy = None
        if env_path.exists():
            with open(env_path, "r") as f:
                for line in f:
                    if line.startswith("TELEGRAM_PROXY="):
                        current_proxy = line.split("=", 1)[1].strip().strip('"').strip("'")
        return current_proxy
    except:
        return None

def fetch_proxies():
    """Fetches fresh proxies from sources."""
    proxies = []
    print("🌐 Fetching fresh proxy lists...")
    
    # 1. Geonode API
    try:
        url = "https://proxylist.geonode.com/api/proxy-list?limit=50&page=1&sort_by=lastChecked&sort_type=desc&protocols=https"
        with urllib.request.urlopen(url, timeout=10) as response:
            data = response.read().decode()
            import json
            json_data = json.loads(data)
            for item in json_data.get("data", []):
                ip = item.get("ip")
                port = item.get("port")
                if ip and port:
                    proxies.append(f"{ip}:{port}")
    except Exception as e:
        print(f"⚠️ Failed to fetch source 1: {e}")

    # 2. Add fallback
    proxies.extend(FALLBACK_PROXIES)
    
    # Remove duplicates
    unique_proxies = list(set(proxies))
    print(f"✅ Found {len(unique_proxies)} potential candidates.")
    return unique_proxies

def test_proxy(proxy_addr):
    """Tests if a specific proxy can reach Telegram API."""
    proxy_url = f"http://{proxy_addr}"
    
    # Create proxy handler
    proxy_handler = urllib.request.ProxyHandler({
        'http': proxy_url,
        'https': proxy_url,
    })
    
    # Setup opener
    opener = urllib.request.build_opener(proxy_handler)
    # Add fake user agent just in case
    opener.addheaders = [('User-agent', 'Mozilla/5.0')]
    
    print(f"   Testing {proxy_addr}...", end=" ")
    sys.stdout.flush()
    
    try:
        start_time = time.time()
        # "getMe" request requires a token, so we just check the root or a safe endpoint
        # Checking root usually returns specific text
        with opener.open(TELEGRAM_TEST_URL, timeout=TIMEOUT) as response:
            code = response.getcode()
            if code in [200, 302, 404]: # 404/302 is fine for root, means we reached server
                duration = time.time() - start_time
                print(f"✅ SUCCESS ({duration:.2f}s)")
                return True
    except urllib.error.HTTPError as e:
        # If we get a 404 from api.telegram.org, we reached it!
        # If we get 407 (Proxy Auth Required), it failed for our purpose (free proxy)
        if e.code == 404: 
             print("✅ SUCCESS (HTTP 404 from Telegram)")
             return True
        print(f"❌ HTTP {e.code}")
    except Exception as e:
        print(f"❌ Failed")
    
    return False

def main():
    print("========================================")
    print("      MAGI PROXY HUNTER v1.0")
    print("========================================")
    
    current = load_env_file_manual()
    if current:
        print(f"ℹ️ Current configured proxy: {current}")
        print("   Retesting current proxy first...")
        if test_proxy(current.replace("http://","").replace("https://","")):
            print("\n🎉 The current proxy IS WORKING! You don't need a new one.")
            sys.exit(0)
        else:
            print("❌ Current proxy is DEAD. Hunting for a new one...\n")

    candidates = fetch_proxies()
    random.shuffle(candidates) # Shuffle to avoid thundering herd on first ones
    
    working_proxy = None
    
    count = 0
    for proxy in candidates:
        if count >= MAX_PROXIES_TO_TEST:
            print("\n⚠️ Reached max test limit.")
            break
            
        if test_proxy(proxy):
            working_proxy = f"http://{proxy}"
            break
        count += 1
        
    print("\n========================================")
    if working_proxy:
        print("🎯 FOUND WORKING PROXY!")
        print(f"   {working_proxy}")
        print("\n👇 ADD THIS TO YOUR .env FILE:")
        print(f"TELEGRAM_PROXY={working_proxy}")
        print("========================================")
    else:
        print("😞 No working proxy found in this batch.")
        print("   Try running the script again to fetch a new list.")
        sys.exit(1)

if __name__ == "__main__":
    main()
