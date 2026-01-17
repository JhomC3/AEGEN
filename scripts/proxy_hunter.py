
import urllib.request
import urllib.error
import random
import time
import socket
import re
import sys
from pathlib import Path

# --- Configuration ---
TIMEOUT = 7
MAX_PROXIES_TO_TEST = 150
TELEGRAM_TEST_URL = "https://api.telegram.org"

def fetch_proxies():
    """Fetches high-quality SOCKS5 and HTTP proxies from 2026 community sources."""
    print("🌐 Fetching fresh proxy lists (SOCKS5/HTTP)...")
    sources = [
        # SOCKS5
        "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=10000&country=all&ssl=all&anonymity=all",
        "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt",
        # HTTP/S
        "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt"
    ]
    
    unique_proxies = set()
    for i, url in enumerate(sources, 1):
        try:
            with urllib.request.urlopen(url, timeout=15) as response:
                content = response.read().decode('utf-8')
                # Find both IP:PORT
                found = re.findall(r'\d+\.\d+\.\d+\.\d+:\d+', content)
                unique_proxies.update(found)
                print(f"✅ Source {i}: Found {len(found)} candidates.")
        except Exception as e:
            print(f"⚠️ Failed to fetch source {i}: {e}")
    
    return list(unique_proxies)

def test_proxy(proxy_addr):
    """
    Tests if a proxy works for Telegram API.
    Since urllib doesn't natively support SOCKS5 without extra libs,
    we test it as an HTTP/HTTPS proxy first (many support both).
    """
    proxy_url = f"http://{proxy_addr}"
    
    proxy_handler = urllib.request.ProxyHandler({'http': proxy_url, 'https': proxy_url})
    opener = urllib.request.build_opener(proxy_handler)
    
    print(f"   Testing {proxy_addr}...", end=" ")
    sys.stdout.flush()
    
    try:
        # We check if we can reach api.telegram.org
        with opener.open(TELEGRAM_TEST_URL, timeout=TIMEOUT) as response:
            if response.getcode() in [200, 404]: # 404 is fine for root
                print("✅ WORKING!")
                return True
    except Exception:
        print("❌")
    return False

def main():
    print("========================================")
    print("      MAGI PROXY HUNTER v2.0 (2026)    ")
    print("========================================")
    
    candidates = fetch_proxies()
    random.shuffle(candidates)
    
    found = None
    count = 0
    for p in candidates:
        if count >= MAX_PROXIES_TO_TEST: break
        if test_proxy(p):
            found = p
            break
        count += 1
        
    if found:
        print("\n🎯 SUCCESS! Add this to your .env:")
        print(f"TELEGRAM_PROXY=http://{found}")
    else:
        print("\n😞 All proxies in this batch failed. GCE might be blocking and you need a private proxy.")

if __name__ == "__main__":
    main()
